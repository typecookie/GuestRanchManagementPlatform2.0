from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from apps.groups.decorators import module_permission_required
from .models import Project, ProjectHistory
from .forms import ProjectForm
from apps.employees.models import Employee

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

@login_required
@module_permission_required('Projects', 'write')
@module_permission_required('Employees', 'write')
def quick_add_project_member(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    project = get_object_or_404(Project, pk=pk)
    name = request.POST.get('name', '').strip()
    position = request.POST.get('position', '').strip()
    role = request.POST.get('role', 'assigned') # 'lead' or 'assigned'
    
    if not name:
        return JsonResponse({'error': 'Name is required'}, status=400)
    
    parts = name.split(' ', 1)
    if len(parts) > 1:
        first_name, last_name = parts
    else:
        first_name = parts[0]
        last_name = "-"
        
    employee = Employee.objects.create(
        first_name=first_name,
        last_name=last_name,
        current_position=position
    )
    
    if role == 'lead':
        project.project_lead = employee
        project.save(update_fields=['project_lead'])
    else:
        project.assigned_employees.add(employee)
        
    return JsonResponse({
        'id': employee.pk,
        'name': str(employee),
        'full_name': employee.full_name,
        'position': employee.current_position,
        'role': role
    })
