from django.urls import path

from . import views


app_name = "reservations"

urlpatterns = [
    path("", views.reservation_list, name="reservation_list"),
    path("grid/", views.reservation_grid, name="reservation_grid"),
    path("new/", views.reservation_create, name="reservation_create"),

    path("<int:pk>/", views.reservation_detail, name="reservation_detail"),
    path("<int:pk>/edit/", views.reservation_update, name="reservation_update"),

    path(
        "<int:pk>/cabins/new/",
        views.reservation_cabin_create,
        name="reservation_cabin_create",
    ),
    path(
        "cabins/<int:pk>/delete/",
        views.reservation_cabin_delete,
        name="reservation_cabin_delete",
    ),

    path(
        "<int:pk>/guests/new/",
        views.reservation_guest_create,
        name="reservation_guest_create",
    ),
    path(
        "<int:pk>/guests/new-client/",
        views.reservation_guest_create_new_client,
        name="reservation_guest_create_new_client",
    ),
    path(
        "<int:pk>/guests/add-household/",
        views.reservation_add_household_guests,
        name="reservation_add_household_guests",
    ),
    path(
        "<int:pk>/guests/add-travel-group/",
        views.reservation_add_travel_group_guests,
        name="reservation_add_travel_group_guests",
    ),
    path(
        "guests/<int:pk>/edit/",
        views.reservation_guest_update,
        name="reservation_guest_update",
    ),
    path(
        "guests/<int:pk>/delete/",
        views.reservation_guest_delete,
        name="reservation_guest_delete",
    ),
    path(
        "api/<int:pk>/quick-add-item/",
        views.quick_add_reservation_item,
        name="quick_add_reservation_item",
    ),
    path(
        "guests/<int:pk>/assign-cabin/",
        views.reservation_guest_assign_cabin,
        name="reservation_guest_assign_cabin",
    ),
    path(
        "guests/<int:pk>/unassign-cabin/",
        views.reservation_guest_unassign_cabin,
        name="reservation_guest_unassign_cabin",
    ),
    path(
        "<int:pk>/toggle-deposit-request/",
        views.reservation_toggle_deposit_request,
        name="reservation_toggle_deposit_request",
    ),
    path(
        "<int:pk>/toggle-deposit-received/",
        views.reservation_toggle_deposit_received,
        name="reservation_toggle_deposit_received",
    ),
    path(
        "guests/<int:pk>/toggle-release/",
        views.reservation_guest_toggle_release,
        name="reservation_guest_toggle_release",
    ),
]