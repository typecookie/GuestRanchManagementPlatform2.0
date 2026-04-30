from django.urls import path

from . import views

app_name = "clients"

urlpatterns = [
    path("", views.contact_dashboard, name="contact_dashboard"),

    path("people/", views.client_list, name="client_list"),
    path("people/new/", views.client_create, name="client_create"),
    path("people/<int:pk>/", views.client_detail, name="client_detail"),
    path("people/<int:pk>/edit/", views.client_update, name="client_update"),
    path("people/<int:pk>/notes/new/", views.client_note_create, name="client_note_create"),

    path("households/", views.household_list, name="household_list"),
    path("households/new/", views.household_create, name="household_create"),
    path("households/<int:pk>/", views.household_detail, name="household_detail"),
    path("households/<int:pk>/edit/", views.household_update, name="household_update"),
    path(
        "households/<int:pk>/members/new/",
        views.household_member_create,
        name="household_member_create",
    ),
    path(
        "household-members/<int:pk>/delete/",
        views.household_member_delete,
        name="household_member_delete",
    ),

    path("travel-groups/", views.travel_group_list, name="travel_group_list"),
    path("travel-groups/new/", views.travel_group_create, name="travel_group_create"),
    path("travel-groups/<int:pk>/", views.travel_group_detail, name="travel_group_detail"),
    path("travel-groups/<int:pk>/edit/", views.travel_group_update, name="travel_group_update"),
    path(
        "travel-groups/<int:pk>/members/new/",
        views.travel_group_member_create,
        name="travel_group_member_create",
    ),
    path(
        "travel-group-members/<int:pk>/delete/",
        views.travel_group_member_delete,
        name="travel_group_member_delete",
    ),
]