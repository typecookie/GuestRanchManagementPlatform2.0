from django.contrib import admin
from .models import Employee, PositionHistory, Interview, StaffSchedule, Department, Position, SeasonPositionTarget

class PositionHistoryInline(admin.TabularInline):
    model = PositionHistory
    extra = 1

class InterviewInline(admin.TabularInline):
    model = Interview
    extra = 1

class PositionInline(admin.TabularInline):
    model = Position
    extra = 1

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'display_order', 'is_default')
    list_filter = ('is_default',)
    search_fields = ('name', 'code', 'description')
    inlines = [PositionInline]

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'is_head', 'default_target_count', 'display_order')
    list_filter = ('department', 'is_head')
    search_fields = ('title', 'department__name', 'description')

@admin.register(SeasonPositionTarget)
class SeasonPositionTargetAdmin(admin.ModelAdmin):
    list_display = ('season', 'position_title', 'department_name', 'target_count')
    list_filter = ('season', 'department')
    search_fields = ('season__name', 'position__title', 'custom_position_title')

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'current_position', 'status', 'user')
    list_filter = ('status',)
    search_fields = ('first_name', 'last_name', 'current_position')
    inlines = [PositionHistoryInline, InterviewInline]

@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ('interviewee_name', 'employee', 'date', 'status', 'is_interviewing')
    list_filter = ('status', 'is_interviewing', 'date')
    search_fields = ('candidate_name', 'employee__first_name', 'employee__last_name', 'notes')


@admin.register(StaffSchedule)
class StaffScheduleAdmin(admin.ModelAdmin):
    list_display = ('position', 'staff_name', 'season', 'department', 'status', 'is_placeholder', 'start_date', 'end_date')
    list_filter = ('season', 'department', 'status', 'is_placeholder', 'position')
    search_fields = ('position', 'placeholder_name', 'employee__first_name', 'employee__last_name', 'notes')
