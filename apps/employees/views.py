from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from apps.groups.decorators import module_permission_required
from .models import Employee, PositionHistory, Interview
from .forms import EmployeeForm, PositionHistoryForm, InterviewForm
from .utils import get_unique_positions
from django.db.models import Q

@login_required
@module_permission_required('Employees', 'read')
def employee_list(request):
    employees = Employee.objects.all()
    status_filter = request.GET.get('status')
    search_query = request.GET.get('q')
    
    if status_filter:
        employees = employees.filter(status=status_filter)
    
    if search_query:
        employees = employees.filter(
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query) |
            Q(current_position__icontains=search_query)
        )
    
    return render(request, 'employees/employee_list.html', {
        'employees': employees,
        'status_choices': Employee.Status.choices,
    })

@login_required
@module_permission_required('Employees', 'read')
def employee_detail(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    position_history = employee.position_history.all()
    interviews = employee.interviews.all().order_by('-date')
    
    return render(request, 'employees/employee_detail.html', {
        'employee': employee,
        'position_history': position_history,
        'interviews': interviews,
    })

@login_required
@module_permission_required('Employees', 'write')
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            employee = form.save()
            return redirect('employees:employee_detail', pk=employee.pk)
    else:
        form = EmployeeForm()
    
    return render(request, 'employees/employee_form.html', {
        'form': form,
        'title': 'Create Employee'
    })

@login_required
@module_permission_required('Employees', 'write')
def employee_update(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            employee = form.save()
            return redirect('employees:employee_detail', pk=employee.pk)
    else:
        form = EmployeeForm(instance=employee)
    
    return render(request, 'employees/employee_form.html', {
        'form': form,
        'employee': employee,
        'title': 'Update Employee'
    })

@login_required
@module_permission_required('Employees', 'write')
def add_position_history(request, employee_pk):
    employee = get_object_or_404(Employee, pk=employee_pk)
    if request.method == 'POST':
        form = PositionHistoryForm(request.POST)
        if form.is_valid():
            history = form.save(commit=False)
            history.employee = employee
            history.save()
            return redirect('employees:employee_detail', pk=employee.pk)
    else:
        form = PositionHistoryForm()
    
    return render(request, 'employees/position_history_form.html', {
        'form': form,
        'employee': employee,
        'title': 'Add Position History'
    })

@login_required
@module_permission_required('Employees', 'write')
def add_interview(request, employee_pk):
    employee = get_object_or_404(Employee, pk=employee_pk)
    if request.method == 'POST':
        form = InterviewForm(request.POST)
        if form.is_valid():
            interview = form.save(commit=False)
            interview.employee = employee
            interview.save()
            return redirect('employees:employee_detail', pk=employee.pk)
    else:
        form = InterviewForm()
    
    return render(request, 'employees/interview_form.html', {
        'form': form,
        'employee': employee,
        'title': 'Add Interview'
    })

@login_required
@module_permission_required('Employees', 'read')
def interview_list(request):
    interviews = Interview.objects.all().select_related('employee')
    status_filter = request.GET.get('status')
    date_sort = request.GET.get('sort', '-date')
    
    if status_filter:
        interviews = interviews.filter(status=status_filter)
    
    interviews = interviews.order_by(date_sort)
    
    return render(request, 'employees/interview_list.html', {
        'interviews': interviews,
        'status_choices': Interview.Status.choices,
    })

@login_required
@module_permission_required('Employees', 'write')
def quick_add_employee(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    name = request.POST.get('name', '').strip()
    position = request.POST.get('position', '').strip()
    
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
    
    return JsonResponse({
        'id': employee.pk,
        'name': str(employee),
        'full_name': employee.full_name,
        'position': employee.current_position
    })

@login_required
@module_permission_required('Employees', 'read')
def api_positions(request):
    positions = get_unique_positions()
    return JsonResponse({'positions': positions})
