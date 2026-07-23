from django.urls import path

from . import views

app_name = "vehicles"

urlpatterns = [
    path("", views.vehicle_list, name="vehicle_list"),
    path("create/", views.vehicle_create, name="vehicle_create"),
    path("<int:pk>/", views.vehicle_detail, name="vehicle_detail"),
    path("<int:pk>/update/", views.vehicle_update, name="vehicle_update"),
    path("<int:pk>/delete/", views.vehicle_delete, name="vehicle_delete"),
    
    # Maintenance Record URLs
    path("<int:vehicle_pk>/maintenance/add/", views.maintenance_record_create, name="maintenance_record_create"),
    path("maintenance/<int:pk>/", views.maintenance_record_detail, name="maintenance_record_detail"),
    path("maintenance/<int:pk>/update/", views.maintenance_record_update, name="maintenance_record_update"),
    path("maintenance/<int:pk>/delete/", views.maintenance_record_delete, name="maintenance_record_delete"),
    
    # Maintenance Step URLs
    path("maintenance/<int:record_pk>/steps/add/", views.maintenance_step_create, name="maintenance_step_create"),
    path("maintenance/steps/<int:pk>/update/", views.maintenance_step_update, name="maintenance_step_update"),
    path("maintenance/steps/<int:pk>/delete/", views.maintenance_step_delete, name="maintenance_step_delete"),
]