from django.urls import path

from . import views

app_name = "horses"

urlpatterns = [
    path("", views.horse_list, name="horse_list"),
    path("create/", views.horse_create, name="horse_create"),
    path("<int:pk>/", views.horse_detail, name="horse_detail"),
    path("<int:pk>/update/", views.horse_update, name="horse_update"),
    path("<int:pk>/delete/", views.horse_delete, name="horse_delete"),
    
    # Saddles
    path("saddles/", views.saddle_list, name="saddle_list"),
    path("saddles/create/", views.saddle_create, name="saddle_create"),
    path("saddles/<int:pk>/", views.saddle_detail, name="saddle_detail"),
    path("saddles/<int:pk>/update/", views.saddle_update, name="saddle_update"),
    path("saddles/<int:pk>/delete/", views.saddle_delete, name="saddle_delete"),
    path("saddles/<int:saddle_pk>/maintenance/create/", views.saddle_maintenance_log_create, name="saddle_maintenance_log_create"),
    path("saddles/maintenance/<int:pk>/delete/", views.saddle_maintenance_log_delete, name="saddle_maintenance_log_delete"),
    
    # Medical History
    path("<int:horse_pk>/medical/create/", views.medical_record_create, name="medical_record_create"),
    path("medical/<int:pk>/", views.medical_record_detail, name="medical_record_detail"),
    path("medical/<int:pk>/update/", views.medical_record_update, name="medical_record_update"),
    path("medical/<int:pk>/delete/", views.medical_record_delete, name="medical_record_delete"),
    
    # Care Steps
    path("medical/<int:record_pk>/care/create/", views.care_step_create, name="care_step_create"),
    path("care/<int:pk>/update/", views.care_step_update, name="care_step_update"),
    path("care/<int:pk>/delete/", views.care_step_delete, name="care_step_delete"),
]