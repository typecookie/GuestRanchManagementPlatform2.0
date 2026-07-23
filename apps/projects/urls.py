from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.kanban_board, name='kanban_board'),
    path('create/', views.project_create, name='project_create'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    path('<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('<int:pk>/update-status/', views.update_project_status, name='update_project_status'),
]
