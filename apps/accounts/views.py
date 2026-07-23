from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User, Group
from django.contrib import messages
from apps.groups.decorators import module_permission_required
from .forms import UserForm

def is_admin(user):
    return user.is_superuser or user.groups.filter(name__in=['Ranch Admins', 'administrator']).exists()

@module_permission_required('User Management', 'read')
def user_list(request):
    users = User.objects.all().prefetch_related('groups')
    return render(request, 'accounts/user_list.html', {'users': users})

@module_permission_required('User Management', 'write')
def user_create(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User {user.username} created successfully.')
            return redirect('accounts:user_list')
    else:
        form = UserForm()
    
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': 'Create User'
    })

@module_permission_required('User Management', 'write')
def user_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User {user.username} updated successfully.')
            return redirect('accounts:user_list')
    else:
        form = UserForm(instance=user)
    
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': f'Edit User: {user.username}'
    })

@module_permission_required('User Management', 'write')
def user_toggle_status(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
    else:
        user.is_active = not user.is_active
        user.save()
        status = "activated" if user.is_active else "deactivated"
        messages.success(request, f"User {user.username} has been {status}.")
    return redirect('accounts:user_list')

@module_permission_required('User Management', 'delete')
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('accounts:user_list')
        
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f"User {username} has been permanently deleted.")
        return redirect('accounts:user_list')
    
    return render(request, 'accounts/user_confirm_delete.html', {'user_to_delete': user})
