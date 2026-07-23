from django.urls import path
from . import views

app_name = 'groups'

urlpatterns = [
    path('', views.group_list, name='group_list'),
    path('create/', views.group_create, name='group_create'),
    path('edit/<int:pk>/', views.group_edit, name='group_edit'),
    path('delete/<int:pk>/', views.group_delete, name='group_delete'),
]
