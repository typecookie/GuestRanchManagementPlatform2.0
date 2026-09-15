from django.urls import path
from . import views

app_name = 'contractors'

urlpatterns = [
    path('', views.contractor_list, name='contractor_list'),
    path('new/', views.contractor_create, name='contractor_create'),
    path('quick-add/', views.quick_add_contractor, name='quick_add_contractor'),
    path('<int:pk>/', views.contractor_detail, name='contractor_detail'),
    path('<int:pk>/edit/', views.contractor_edit, name='contractor_edit'),
    path('<int:pk>/delete/', views.contractor_delete, name='contractor_delete'),
]
