from django.urls import path
from . import views

app_name = 'employees'

urlpatterns = [
    path('', views.employee_list, name='employee_list'),
    path('create/', views.employee_create, name='employee_create'),
    path('<int:pk>/', views.employee_detail, name='employee_detail'),
    path('<int:pk>/update/', views.employee_update, name='employee_update'),
    path('<int:employee_pk>/position-history/add/', views.add_position_history, name='add_position_history'),
    path('<int:employee_pk>/interview/add/', views.add_interview, name='add_interview'),
    path('interviews/', views.interview_list, name='interview_list'),
    path('interviews/create/', views.interview_create, name='interview_create'),
    path('interviews/<int:pk>/edit/', views.interview_update, name='interview_update'),
    path('interviews/<int:pk>/delete/', views.interview_delete, name='interview_delete'),
    path('interviews/<int:pk>/hire/', views.hire_candidate, name='hire_candidate'),
    path('staffing/', views.staffing_schedule, name='staffing_schedule'),
    path('staffing/create/', views.staff_schedule_create, name='staff_schedule_create'),
    path('staffing/<int:pk>/edit/', views.staff_schedule_update, name='staff_schedule_update'),
    path('staffing/<int:pk>/delete/', views.staff_schedule_delete, name='staff_schedule_delete'),
    path('staffing/<int:pk>/link/', views.staff_schedule_link_employee, name='staff_schedule_link_employee'),
    path('api/quick-add/', views.quick_add_employee, name='quick_add_employee'),
    path('api/positions/', views.api_positions, name='api_positions'),
]
