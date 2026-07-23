from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from apps.groups.decorators import module_permission_required
from .models import Project, ProjectHistory
from .forms import ProjectForm

@module_permission_required('Projects', 'read')
def kanban_board(request):
    projects = Project.objects.all()
    statuses = Project.Status.choices
    
    # Group projects by status
    board_data = {status[0]: [] for status in statuses}
    for project in projects:
        board_data[project.status].append(project)
    
    context = {
        'board_data': board_data,
        'statuses': statuses,
    }
    return render(request, 'projects/kanban_board.html', context)


@module_permission_required('Projects', 'read')
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render(request, 'projects/project_detail.html', {'project': project})


@module_permission_required('Projects', 'write')
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('projects:kanban_board')
    else:
        form = ProjectForm()
    
    return render(request, 'projects/project_form.html', {'form': form})


@module_permission_required('Projects', 'write')
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    
    return render(request, 'projects/project_form.html', {
        'project': project,
        'form': form,
    })


@module_permission_required('Projects', 'delete')
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        project.delete()
        return redirect('projects:kanban_board')
    return render(request, 'projects/project_confirm_delete.html', {'project': project})


@module_permission_required('Projects', 'write')
@require_POST
def update_project_status(request, pk):
    project = get_object_or_404(Project, pk=pk)
    new_status = request.POST.get('status')
    
    if new_status in dict(Project.Status.choices):
        project.status = new_status
        project.save()
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid status'}, status=400)
