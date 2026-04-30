from django.urls import path

from . import views

app_name = "ranch"

urlpatterns = [
    path("", views.ranch_operations, name="ranch_operations"),
    path("office/", views.office_dashboard, name="office_dashboard"),
    path(
        "office/reports/dining-guest-list/",
        views.weekly_dining_guest_list_report,
        name="weekly_dining_guest_list_report",
    ),
]