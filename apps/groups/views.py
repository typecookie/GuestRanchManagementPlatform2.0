from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from apps.groups.decorators import module_permission_required
from .utils import get_module_permissions, set_module_permissions, MODULE_MAPPING

@module_permission_required('Group Management', 'read')
def group_list(request):
    groups = Group.objects.all().order_by('name')
    return render(request, 'groups/group_list.html', {'groups': groups})

@module_permission_required('Group Management', 'write')
def group_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            group, created = Group.objects.get_or_create(name=name)
            if created:
                messages.success(request, f'Group "{name}" created successfully.')
                return redirect('groups:group_edit', pk=group.pk)
            else:
                messages.error(request, f'Group "{name}" already exists.')
    
    return render(request, 'groups/group_form.html', {'title': 'Create Group'})

@module_permission_required('Group Management', 'write')
def group_edit(request, pk):
    group = get_object_or_404(Group, pk=pk)
    
    if request.method == 'POST':
        group.name = request.POST.get('name')
        group.save()
        
        # Process permissions
        for module in MODULE_MAPPING.keys():
            read_val = request.POST.get(f'perm_{module}_read') == 'on'
            write_val = request.POST.get(f'perm_{module}_write') == 'on'
            delete_val = request.POST.get(f'perm_{module}_delete') == 'on'
            
            set_module_permissions(group, module, 'read', read_val)
            set_module_permissions(group, module, 'write', write_val)
            set_module_permissions(group, module, 'delete', delete_val)
            
        messages.success(request, f'Group "{group.name}" updated successfully.')
        return redirect('groups:group_list')
    
    module_perms = get_module_permissions(group)
    return render(request, 'groups/group_form.html', {
        'group': group,
        'module_perms': module_perms,
        'title': f'Edit Group: {group.name}'
    })

@module_permission_required('Group Management', 'delete')
def group_delete(request, pk):
    group = get_object_or_404(Group, pk=pk)
    if request.method == 'POST':
        name = group.name
        group.delete()
        messages.success(request, f'Group "{name}" deleted successfully.')
        return redirect('groups:group_list')
    
    return render(request, 'groups/group_confirm_delete.html', {'group': group})
