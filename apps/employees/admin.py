from django.contrib import admin
from .models import Employee, PositionHistory, Interview

class PositionHistoryInline(admin.TabularInline):
    model = PositionHistory
    extra = 1

class InterviewInline(admin.TabularInline):
    model = Interview
    extra = 1

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'current_position', 'status', 'user')
    list_filter = ('status',)
    search_fields = ('first_name', 'last_name', 'current_position')
    inlines = [PositionHistoryInline, InterviewInline]

@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'status', 'is_interviewing')
    list_filter = ('status', 'is_interviewing', 'date')
    search_fields = ('employee__first_name', 'employee__last_name', 'notes')
