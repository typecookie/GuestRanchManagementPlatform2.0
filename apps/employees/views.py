from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from datetime import date, timedelta
from apps.groups.decorators import module_permission_required
from .models import Employee, PositionHistory, Interview, StaffSchedule, Department, Position, SeasonPositionTarget
from .forms import (
    EmployeeForm, PositionHistoryForm, InterviewForm,
    StaffScheduleForm, StaffScheduleLinkEmployeeForm,
    DepartmentForm, PositionForm, SeasonPositionTargetForm
)
from .utils import (
    get_unique_positions, ensure_default_departments_and_positions,
    sync_season_targets_from_schedule, auto_fill_schedule_from_season_targets
)
from apps.reservations.models import OperatingSeason
from apps.reservations.season_utils import get_categorized_seasons, get_default_season_dates
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
    staff_schedules = employee.staff_schedules.all().order_by('-start_date')
    
    return render(request, 'employees/employee_detail.html', {
        'employee': employee,
        'position_history': position_history,
        'interviews': interviews,
        'staff_schedules': staff_schedules,
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
        form = InterviewForm(request.POST, employee=employee)
        if form.is_valid():
            interview = form.save(commit=False)
            interview.employee = employee
            interview.save()
            return redirect('employees:employee_detail', pk=employee.pk)
    else:
        form = InterviewForm(employee=employee, initial={'employee': employee})
    
    return render(request, 'employees/interview_form.html', {
        'form': form,
        'employee': employee,
        'title': f'Add Interview for {employee.full_name}',
    })

@login_required
@module_permission_required('Employees', 'write')
def interview_create(request):
    if request.method == 'POST':
        form = InterviewForm(request.POST)
        if form.is_valid():
            interview = form.save()
            if interview.employee:
                return redirect('employees:employee_detail', pk=interview.employee.pk)
            return redirect('employees:interview_list')
    else:
        form = InterviewForm()
    
    return render(request, 'employees/interview_form.html', {
        'form': form,
        'title': 'Add Interview',
    })

@login_required
@module_permission_required('Employees', 'write')
def interview_update(request, pk):
    interview = get_object_or_404(Interview, pk=pk)
    if request.method == 'POST':
        form = InterviewForm(request.POST, instance=interview)
        if form.is_valid():
            form.save()
            messages.success(request, f'Interview for {interview.interviewee_name} updated successfully.')
            if interview.employee:
                return redirect('employees:employee_detail', pk=interview.employee.pk)
            return redirect('employees:interview_list')
    else:
        form = InterviewForm(instance=interview)
    
    return render(request, 'employees/interview_form.html', {
        'form': form,
        'interview': interview,
        'employee': interview.employee,
        'title': f'Edit Interview: {interview.interviewee_name}',
    })

@login_required
@module_permission_required('Employees', 'delete')
def interview_delete(request, pk):
    interview = get_object_or_404(Interview, pk=pk)
    employee = interview.employee
    interviewee = interview.interviewee_name
    interview_date = interview.date
    if request.method == 'POST':
        interview.delete()
        messages.success(request, f'Interview for {interviewee} on {interview_date} was deleted successfully.')
        if employee:
            return redirect('employees:employee_detail', pk=employee.pk)
        return redirect('employees:interview_list')
    
    return render(request, 'employees/interview_confirm_delete.html', {
        'interview': interview,
        'employee': employee,
    })

@login_required
@module_permission_required('Employees', 'write')
def hire_candidate(request, pk):
    interview = get_object_or_404(Interview, pk=pk)
    
    # If already linked to an employee, redirect to profile
    if interview.employee:
        return redirect('employees:employee_detail', pk=interview.employee.pk)
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            employee = form.save()
            interview.employee = employee
            interview.save()
            
            # Record initial position history if position was specified
            if employee.current_position:
                PositionHistory.objects.create(
                    employee=employee,
                    position=employee.current_position,
                    start_date=interview.date,
                    notes=f"Hired from candidate interview conducted on {interview.date}"
                )
            
            return redirect('employees:employee_detail', pk=employee.pk)
    else:
        candidate_name = interview.candidate_name.strip() if interview.candidate_name else ""
        first_name = ""
        last_name = ""
        if candidate_name:
            parts = candidate_name.split(' ', 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else "-"
            
        initial_data = {
            'first_name': first_name,
            'last_name': last_name,
            'current_position': interview.offered_position or "",
            'status': Employee.Status.ACTIVE,
            'performance_notes': f"Hired from candidate interview conducted on {interview.date}.\nNotes: {interview.notes}".strip() if interview.notes else f"Hired from candidate interview conducted on {interview.date}."
        }
        form = EmployeeForm(initial=initial_data)
    
    return render(request, 'employees/hire_candidate.html', {
        'form': form,
        'interview': interview,
        'title': f'Hire Candidate: {interview.interviewee_name}',
    })

@login_required
@module_permission_required('Employees', 'read')
def interview_list(request):
    interviews = Interview.objects.all().select_related('employee')
    status_filter = request.GET.get('status')
    type_filter = request.GET.get('type')
    search_query = request.GET.get('q')
    date_sort = request.GET.get('sort', '-date')
    
    if status_filter:
        interviews = interviews.filter(status=status_filter)
    
    if type_filter == 'candidate':
        interviews = interviews.filter(employee__isnull=True)
    elif type_filter == 'employee':
        interviews = interviews.filter(employee__isnull=False)

    if search_query:
        interviews = interviews.filter(
            Q(employee__first_name__icontains=search_query) |
            Q(employee__last_name__icontains=search_query) |
            Q(candidate_name__icontains=search_query) |
            Q(notes__icontains=search_query) |
            Q(offered_position__icontains=search_query)
        )
    
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


@login_required
@module_permission_required('Employees', 'read')
def staffing_schedule(request):
    ensure_default_departments_and_positions()
    today = date.today()
    categorized_seasons = get_categorized_seasons(today)
    default_season = categorized_seasons.get("default_season")
    
    all_seasons = OperatingSeason.objects.all().order_by('-start_date')
    
    season_id = request.GET.get('season')
    selected_season = None
    if season_id and season_id.isdigit():
        selected_season = OperatingSeason.objects.filter(pk=int(season_id)).first()
    
    if not selected_season:
        selected_season = default_season or all_seasons.first()

    if selected_season:
        season_start = selected_season.start_date
        season_end = selected_season.end_date
        season_name = selected_season.name
        # Ensure season targets are synced
        if not selected_season.position_targets.exists():
            sync_season_targets_from_schedule(selected_season)
    else:
        season_start, season_end = get_default_season_dates(today.year)
        season_name = f"Season {today.year}"

    # Timeline bounds: exactly 2 weeks before opening date, 2 weeks after closing date
    timeline_start = season_start - timedelta(days=14)
    timeline_end = season_end + timedelta(days=14)
    total_days = max(1, (timeline_end - timeline_start).days + 1)

    # Build weekly columns across the entire season timeline
    weeks = []
    current_date = timeline_start
    week_idx = 1
    while current_date <= timeline_end:
        w_start = current_date
        w_end = min(timeline_end, current_date + timedelta(days=6))
        
        has_opening = (w_start <= season_start <= w_end)
        has_closing = (w_start <= season_end <= w_end)
        is_pre_season = (w_end < season_start)
        is_post_season = (w_start > season_end)
        is_in_season = not is_pre_season and not is_post_season
        
        weeks.append({
            'index': week_idx,
            'start_date': w_start,
            'end_date': w_end,
            'label': w_start.strftime('%b %d'),
            'date_range': f"{w_start.strftime('%b %d')} – {w_end.strftime('%b %d')}",
            'month_name': w_start.strftime('%b'),
            'has_opening': has_opening,
            'has_closing': has_closing,
            'is_pre_season': is_pre_season,
            'is_post_season': is_post_season,
            'is_in_season': is_in_season,
        })
        current_date += timedelta(days=7)
        week_idx += 1

    # Header month grouping
    month_groups = []
    for week in weeks:
        m_name = week['start_date'].strftime('%B %Y')
        if month_groups and month_groups[-1]['name'] == m_name:
            month_groups[-1]['col_span'] += 1
        else:
            month_groups.append({
                'name': m_name,
                'short_name': week['start_date'].strftime('%b'),
                'col_span': 1
            })

    # Query staffing schedule items
    schedules_qs = StaffSchedule.objects.select_related('employee', 'season', 'department')
    if selected_season:
        schedules_qs = schedules_qs.filter(
            Q(season=selected_season) |
            (Q(season__isnull=True) & Q(start_date__lte=timeline_end, end_date__gte=timeline_start))
        )
    else:
        schedules_qs = schedules_qs.filter(start_date__lte=timeline_end, end_date__gte=timeline_start)

    search_query = request.GET.get('q', '').strip()
    if search_query:
        schedules_qs = schedules_qs.filter(
            Q(position__icontains=search_query) |
            Q(placeholder_name__icontains=search_query) |
            Q(employee__first_name__icontains=search_query) |
            Q(employee__last_name__icontains=search_query) |
            Q(department__name__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    department_filter = request.GET.get('department', '').strip()
    if department_filter:
        schedules_qs = schedules_qs.filter(
            Q(department__name__iexact=department_filter) |
            Q(department__code__iexact=department_filter)
        )

    position_filter = request.GET.get('position', '').strip()
    if position_filter:
        schedules_qs = schedules_qs.filter(position=position_filter)

    status_filter = request.GET.get('status', '').strip()
    if status_filter == 'confirmed':
        schedules_qs = schedules_qs.filter(is_placeholder=False, status=StaffSchedule.Status.CONFIRMED)
    elif status_filter == 'tentative':
        schedules_qs = schedules_qs.filter(status=StaffSchedule.Status.TENTATIVE)
    elif status_filter in ['placeholder', 'unconfirmed']:
        schedules_qs = schedules_qs.filter(Q(is_placeholder=True) | Q(status=StaffSchedule.Status.UNCONFIRMED))

    schedules_qs = schedules_qs.order_by('department__display_order', 'position', 'start_date', 'employee__last_name', 'placeholder_name')

    all_positions = get_unique_positions()
    all_departments = Department.objects.all().order_by('display_order', 'name')

    schedule_rows = []
    confirmed_count = 0
    tentative_count = 0
    placeholder_count = 0
    positions_seen = set()

    for item in schedules_qs:
        if item.status == StaffSchedule.Status.TENTATIVE:
            tentative_count += 1
        elif item.is_placeholder or item.status == StaffSchedule.Status.UNCONFIRMED:
            placeholder_count += 1
        else:
            confirmed_count += 1
            
        if item.position:
            positions_seen.add(item.position)

        clamped_start = max(timeline_start, item.start_date)
        clamped_end = min(timeline_end, item.end_date)
        
        offset_days = max(0, (clamped_start - timeline_start).days)
        active_days = max(1, (clamped_end - clamped_start).days + 1)
        
        left_pct = round(max(0.0, min(100.0, (offset_days / total_days) * 100)), 2)
        width_pct = round(max(2.0, min(100.0 - left_pct, (active_days / total_days) * 100)), 2)

        week_statuses = []
        for week in weeks:
            is_active = (item.start_date <= week['end_date'] and item.end_date >= week['start_date'])
            is_start = (week['start_date'] <= item.start_date <= week['end_date'])
            is_end = (week['start_date'] <= item.end_date <= week['end_date'])
            week_statuses.append({
                'is_active': is_active,
                'is_start': is_start,
                'is_end': is_end,
                'week_index': week['index'],
            })

        dept_name = item.department.name if item.department else 'General'

        schedule_rows.append({
            'schedule': item,
            'status': item.status,
            'is_tentative': (item.status == StaffSchedule.Status.TENTATIVE),
            'is_placeholder': (item.is_placeholder or item.status == StaffSchedule.Status.UNCONFIRMED),
            'is_confirmed': (item.status == StaffSchedule.Status.CONFIRMED and not item.is_placeholder),
            'staff_name': item.staff_name,
            'position': item.position,
            'department_name': dept_name,
            'start_date': item.start_date,
            'end_date': item.end_date,
            'duration_days': item.duration_days,
            'duration_weeks': item.duration_weeks,
            'left_percent': left_pct,
            'width_percent': width_pct,
            'week_statuses': week_statuses,
            'starts_before': item.start_date < timeline_start,
            'ends_after': item.end_date > timeline_end,
        })

    target_count_total = 0
    if selected_season:
        target_count_total = sum(t.target_count for t in selected_season.position_targets.all())

    return render(request, 'employees/staffing_schedule.html', {
        'selected_season': selected_season,
        'all_seasons': all_seasons,
        'categorized_seasons': categorized_seasons,
        'season_name': season_name,
        'season_start': season_start,
        'season_end': season_end,
        'timeline_start': timeline_start,
        'timeline_end': timeline_end,
        'total_days': total_days,
        'weeks': weeks,
        'month_groups': month_groups,
        'schedule_rows': schedule_rows,
        'total_count': len(schedule_rows),
        'confirmed_count': confirmed_count,
        'tentative_count': tentative_count,
        'placeholder_count': placeholder_count,
        'target_count_total': target_count_total,
        'positions_count': len(positions_seen),
        'all_positions': all_positions,
        'all_departments': all_departments,
        'search_query': search_query,
        'department_filter': department_filter,
        'position_filter': position_filter,
        'status_filter': status_filter,
    })


@login_required
@module_permission_required('Employees', 'write')
def staff_schedule_create(request):
    season_id = request.GET.get('season')
    selected_season = None
    if season_id and season_id.isdigit():
        selected_season = OperatingSeason.objects.filter(pk=int(season_id)).first()

    initial = {}
    if selected_season:
        initial['season'] = selected_season
        initial['start_date'] = selected_season.start_date
        initial['end_date'] = selected_season.end_date

    dept_id = request.GET.get('department')
    if dept_id and dept_id.isdigit():
        initial['department'] = Department.objects.filter(pk=int(dept_id)).first()

    if request.method == 'POST':
        form = StaffScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save()
            messages.success(request, f"Staffing assignment for '{schedule.staff_name}' as {schedule.position} was added successfully.")
            redirect_url = redirect('employees:staffing_schedule').url
            if schedule.season:
                redirect_url += f"?season={schedule.season.pk}"
            return redirect(redirect_url)
    else:
        form = StaffScheduleForm(initial=initial)

    return render(request, 'employees/staff_schedule_form.html', {
        'form': form,
        'title': 'Add Staff Position / Schedule',
        'selected_season': selected_season,
    })


@login_required
@module_permission_required('Employees', 'write')
def staff_schedule_update(request, pk):
    schedule = get_object_or_404(StaffSchedule, pk=pk)
    
    if request.method == 'POST':
        form = StaffScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            schedule = form.save()
            messages.success(request, f"Staffing assignment for '{schedule.staff_name}' updated successfully.")
            redirect_url = redirect('employees:staffing_schedule').url
            if schedule.season:
                redirect_url += f"?season={schedule.season.pk}"
            return redirect(redirect_url)
    else:
        form = StaffScheduleForm(instance=schedule)

    return render(request, 'employees/staff_schedule_form.html', {
        'form': form,
        'schedule': schedule,
        'title': f"Edit Staff Assignment: {schedule.staff_name}",
        'selected_season': schedule.season,
    })


@login_required
@module_permission_required('Employees', 'delete')
def staff_schedule_delete(request, pk):
    schedule = get_object_or_404(StaffSchedule, pk=pk)
    season = schedule.season
    staff_name = schedule.staff_name
    position = schedule.position

    if request.method == 'POST':
        schedule.delete()
        messages.success(request, f"Staffing assignment for {staff_name} ({position}) was deleted successfully.")
        redirect_url = redirect('employees:staffing_schedule').url
        if season:
            redirect_url += f"?season={season.pk}"
        return redirect(redirect_url)

    return render(request, 'employees/staff_schedule_confirm_delete.html', {
        'schedule': schedule,
        'season': season,
    })


@login_required
@module_permission_required('Employees', 'write')
def staff_schedule_link_employee(request, pk):
    schedule = get_object_or_404(StaffSchedule, pk=pk)
    
    if request.method == 'POST':
        form = StaffScheduleLinkEmployeeForm(request.POST)
        if form.is_valid():
            employee = form.cleaned_data['employee']
            schedule.employee = employee
            schedule.is_placeholder = False
            schedule.placeholder_name = ''
            schedule.status = form.cleaned_data['status']
            if form.cleaned_data['notes']:
                schedule.notes = (schedule.notes + "\n" + form.cleaned_data['notes']).strip()
            schedule.save()
            messages.success(request, f"Linked placeholder position to {employee.full_name} successfully.")
            redirect_url = redirect('employees:staffing_schedule').url
            if schedule.season:
                redirect_url += f"?season={schedule.season.pk}"
            return redirect(redirect_url)
    else:
        form = StaffScheduleLinkEmployeeForm(initial={'status': StaffSchedule.Status.CONFIRMED})

    return render(request, 'employees/staff_schedule_link.html', {
        'form': form,
        'schedule': schedule,
    })


# ==============================================================================
# DEPARTMENTS & POSITIONS MANAGEMENT
# ==============================================================================

@login_required
@module_permission_required('Employees', 'read')
def department_position_list(request):
    ensure_default_departments_and_positions()
    departments = Department.objects.prefetch_related('positions').order_by('display_order', 'name')
    all_seasons = OperatingSeason.objects.all().order_by('-start_date')
    
    return render(request, 'employees/department_position_list.html', {
        'departments': departments,
        'all_seasons': all_seasons,
        'total_positions': Position.objects.count(),
        'total_departments': departments.count(),
    })


@login_required
@module_permission_required('Employees', 'write')
def department_create(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            dept = form.save()
            messages.success(request, f"Department '{dept.name}' was created successfully.")
            return redirect('employees:department_position_list')
    else:
        form = DepartmentForm()

    return render(request, 'employees/department_form.html', {
        'form': form,
        'title': 'Add New Department',
    })


@login_required
@module_permission_required('Employees', 'write')
def department_update(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            dept = form.save()
            messages.success(request, f"Department '{dept.name}' was updated successfully.")
            return redirect('employees:department_position_list')
    else:
        form = DepartmentForm(instance=dept)

    return render(request, 'employees/department_form.html', {
        'form': form,
        'department': dept,
        'title': f"Edit Department: {dept.name}",
    })


@login_required
@module_permission_required('Employees', 'delete')
def department_delete(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    name = dept.name
    if request.method == 'POST':
        dept.delete()
        messages.success(request, f"Department '{name}' was deleted.")
        return redirect('employees:department_position_list')

    return render(request, 'employees/department_confirm_delete.html', {
        'department': dept,
    })


@login_required
@module_permission_required('Employees', 'write')
def position_create(request):
    initial = {}
    dept_id = request.GET.get('department')
    if dept_id and dept_id.isdigit():
        initial['department'] = get_object_or_404(Department, pk=int(dept_id))

    if request.method == 'POST':
        form = PositionForm(request.POST)
        if form.is_valid():
            pos = form.save()
            messages.success(request, f"Position '{pos.title}' added to {pos.department.name} department.")
            return redirect('employees:department_position_list')
    else:
        form = PositionForm(initial=initial)

    return render(request, 'employees/position_form.html', {
        'form': form,
        'title': 'Add New Position',
    })


@login_required
@module_permission_required('Employees', 'write')
def position_update(request, pk):
    pos = get_object_or_404(Position, pk=pk)
    if request.method == 'POST':
        form = PositionForm(request.POST, instance=pos)
        if form.is_valid():
            pos = form.save()
            messages.success(request, f"Position '{pos.title}' updated successfully.")
            return redirect('employees:department_position_list')
    else:
        form = PositionForm(instance=pos)

    return render(request, 'employees/position_form.html', {
        'form': form,
        'position': pos,
        'title': f"Edit Position: {pos.title}",
    })


@login_required
@module_permission_required('Employees', 'delete')
def position_delete(request, pk):
    pos = get_object_or_404(Position, pk=pk)
    title = pos.title
    dept_name = pos.department.name
    if request.method == 'POST':
        pos.delete()
        messages.success(request, f"Position '{title}' ({dept_name}) was deleted.")
        return redirect('employees:department_position_list')

    return render(request, 'employees/position_confirm_delete.html', {
        'position': pos,
    })


# ==============================================================================
# OPERATING DATES / SEASON STAFFING TARGETS & AUTO-FILL
# ==============================================================================

@login_required
@module_permission_required('Employees', 'read')
def season_staffing_plan(request, season_id):
    season = get_object_or_404(OperatingSeason, pk=season_id)
    ensure_default_departments_and_positions()
    
    # Sync targets if none exist or when requested
    if not season.position_targets.exists():
        sync_season_targets_from_schedule(season)

    departments = Department.objects.prefetch_related('positions').order_by('display_order', 'name')
    targets = season.position_targets.select_related('department', 'position').order_by('department__display_order', 'position__display_order', 'id')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'save_targets':
            for target in targets:
                input_key = f"target_{target.pk}"
                if input_key in request.POST:
                    try:
                        val = int(request.POST[input_key])
                        if val >= 0:
                            target.target_count = val
                            target.save()
                    except ValueError:
                        pass
            
            auto_fill = request.POST.get('auto_fill_after_save') == '1'
            if auto_fill:
                count = auto_fill_schedule_from_season_targets(season)
                messages.success(request, f"Saved target headcounts and auto-filled {count} missing positions into the Staffing Schedule.")
            else:
                messages.success(request, f"Staffing targets for {season.name} saved successfully.")
            return redirect('employees:season_staffing_plan', season_id=season.pk)

        elif action == 'auto_fill':
            count = auto_fill_schedule_from_season_targets(season)
            messages.success(request, f"Auto-filled {count} missing positions into the Staffing Schedule for {season.name}.")
            return redirect('employees:season_staffing_plan', season_id=season.pk)

        elif action == 'sync_from_schedule':
            sync_season_targets_from_schedule(season)
            messages.success(request, f"Synchronized position target headcounts from current Staffing Schedule.")
            return redirect('employees:season_staffing_plan', season_id=season.pk)

        elif action == 'add_custom_position':
            dept_id = request.POST.get('department_id')
            pos_title = request.POST.get('position_title', '').strip()
            target_count = int(request.POST.get('target_count', 1) or 1)
            create_master = request.POST.get('create_master') == '1'

            if pos_title:
                dept = Department.objects.filter(pk=dept_id).first() if dept_id else None
                master_pos = None
                if create_master and dept:
                    master_pos, _ = Position.objects.get_or_create(
                        department=dept,
                        title=pos_title,
                        defaults={'default_target_count': target_count}
                    )
                
                SeasonPositionTarget.objects.create(
                    season=season,
                    department=dept,
                    position=master_pos,
                    custom_position_title=pos_title if not master_pos else '',
                    target_count=target_count
                )
                messages.success(request, f"Added position target '{pos_title}' to {season.name}.")
            return redirect('employees:season_staffing_plan', season_id=season.pk)

    # Prepare structured department target data for rendering
    dept_plans = []
    total_planned = 0
    total_scheduled = 0
    total_confirmed = 0
    total_placeholders = 0
    total_tentative = 0

    target_map = {t.position.pk if t.position else f"c_{t.custom_position_title.lower()}": t for t in targets}

    for dept in departments:
        dept_rows = []
        for pos in dept.positions.all():
            target_obj = target_map.get(pos.pk)
            if not target_obj:
                target_obj = SeasonPositionTarget.objects.create(
                    season=season,
                    department=dept,
                    position=pos,
                    target_count=pos.default_target_count
                )
            
            scheduled = target_obj.get_scheduled_count()
            confirmed = target_obj.get_confirmed_count()
            placeholders = target_obj.get_placeholder_count()
            tentative = target_obj.get_tentative_count()

            total_planned += target_obj.target_count
            total_scheduled += scheduled
            total_confirmed += confirmed
            total_placeholders += placeholders
            total_tentative += tentative

            dept_rows.append({
                'target': target_obj,
                'position': pos,
                'title': pos.title,
                'is_head': pos.is_head,
                'target_count': target_obj.target_count,
                'scheduled_count': scheduled,
                'confirmed_count': confirmed,
                'placeholder_count': placeholders,
                'tentative_count': tentative,
                'difference': target_obj.target_count - scheduled,
            })

        dept_plans.append({
            'department': dept,
            'rows': dept_rows,
            'planned_total': sum(r['target_count'] for r in dept_rows),
            'scheduled_total': sum(r['scheduled_count'] for r in dept_rows),
            'confirmed_total': sum(r['confirmed_count'] for r in dept_rows),
        })

    # Unassigned or custom targets not in master positions
    custom_targets = targets.filter(position__isnull=True)
    custom_rows = []
    for ct in custom_targets:
        scheduled = ct.get_scheduled_count()
        confirmed = ct.get_confirmed_count()
        placeholders = ct.get_placeholder_count()
        tentative = ct.get_tentative_count()

        total_planned += ct.target_count
        total_scheduled += scheduled
        total_confirmed += confirmed
        total_placeholders += placeholders
        total_tentative += tentative

        custom_rows.append({
            'target': ct,
            'position': None,
            'title': ct.custom_position_title,
            'is_head': False,
            'target_count': ct.target_count,
            'scheduled_count': scheduled,
            'confirmed_count': confirmed,
            'placeholder_count': placeholders,
            'tentative_count': tentative,
            'difference': ct.target_count - scheduled,
        })

    all_seasons = OperatingSeason.objects.all().order_by('-start_date')

    return render(request, 'employees/season_staffing_plan.html', {
        'season': season,
        'all_seasons': all_seasons,
        'departments': departments,
        'dept_plans': dept_plans,
        'custom_rows': custom_rows,
        'total_planned': total_planned,
        'total_scheduled': total_scheduled,
        'total_confirmed': total_confirmed,
        'total_placeholders': total_placeholders,
        'total_tentative': total_tentative,
    })


@login_required
@module_permission_required('Employees', 'write')
def season_staffing_auto_fill(request, season_id):
    season = get_object_or_404(OperatingSeason, pk=season_id)
    count = auto_fill_schedule_from_season_targets(season)
    messages.success(request, f"Auto-filled {count} missing position placeholders for '{season.name}' into the Staffing Schedule.")
    
    redirect_target = request.GET.get('from')
    if redirect_target == 'operating_dates':
        return redirect('reservations:operating_dates_list')
    elif redirect_target == 'schedule':
        return redirect(f"{redirect('employees:staffing_schedule').url}?season={season.pk}")
    return redirect('employees:season_staffing_plan', season_id=season.pk)


@login_required
@module_permission_required('Employees', 'write')
def season_staffing_sync(request, season_id):
    season = get_object_or_404(OperatingSeason, pk=season_id)
    sync_season_targets_from_schedule(season)
    messages.success(request, f"Synchronized staffing targets for '{season.name}' from current schedule records.")
    
    redirect_target = request.GET.get('from')
    if redirect_target == 'operating_dates':
        return redirect('reservations:operating_dates_list')
    elif redirect_target == 'schedule':
        return redirect(f"{redirect('employees:staffing_schedule').url}?season={season.pk}")
    return redirect('employees:season_staffing_plan', season_id=season.pk)
