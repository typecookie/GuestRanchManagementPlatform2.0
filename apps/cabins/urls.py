from django.urls import path

from . import views

app_name = "cabins"

urlpatterns = [
    path("", views.cabin_list, name="cabin_list"),
    path("new/", views.cabin_create, name="cabin_create"),
    path("<int:pk>/", views.cabin_detail, name="cabin_detail"),
    path("<int:pk>/edit/", views.cabin_update, name="cabin_update"),
    
    # Inventory Items
    path("<int:cabin_pk>/inventory/new/", views.cabin_inventory_item_create, name="cabin_inventory_item_create"),
    path("inventory/<int:pk>/", views.cabin_inventory_item_detail, name="cabin_inventory_item_detail"),
    path("inventory/<int:pk>/edit/", views.cabin_inventory_item_update, name="cabin_inventory_item_update"),
    path("inventory/<int:pk>/delete/", views.cabin_inventory_item_delete, name="cabin_inventory_item_delete"),
    
    # Inventory Item Maintenance Logs
    path("inventory/<int:item_pk>/maintenance/new/", views.cabin_item_maintenance_log_create, name="cabin_item_maintenance_log_create"),
    path("inventory/maintenance/<int:pk>/edit/", views.cabin_item_maintenance_log_update, name="cabin_item_maintenance_log_update"),
    path("inventory/maintenance/<int:pk>/delete/", views.cabin_item_maintenance_log_delete, name="cabin_item_maintenance_log_delete"),
]