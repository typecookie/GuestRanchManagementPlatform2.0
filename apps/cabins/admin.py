from django.contrib import admin

from .models import Cabin, CabinInventoryItem, CabinInventoryMaintenanceLog


@admin.register(Cabin)
class CabinAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "cabin_number",
        "capacity",
        "status",
        "housekeeping_status",
        "is_active",
        "sort_order",
    ]
    list_filter = [
        "status",
        "housekeeping_status",
        "is_active",
    ]
    search_fields = [
        "name",
        "cabin_number",
        "bed_configuration",
        "description",
        "notes",
    ]
    ordering = [
        "sort_order",
        "name",
    ]


@admin.register(CabinInventoryItem)
class CabinInventoryItemAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "cabin",
        "category",
        "brand",
        "model_number",
        "serial_number",
        "condition",
        "status",
    ]
    list_filter = [
        "category",
        "status",
        "condition",
        "cabin",
    ]
    search_fields = [
        "name",
        "brand",
        "model_number",
        "serial_number",
        "location_in_cabin",
        "notes",
    ]


@admin.register(CabinInventoryMaintenanceLog)
class CabinInventoryMaintenanceLogAdmin(admin.ModelAdmin):
    list_display = [
        "date",
        "item",
        "title",
        "performed_by",
        "cost",
        "status_update",
    ]
    list_filter = [
        "status_update",
        "date",
    ]
    search_fields = [
        "title",
        "performed_by",
        "work_performed",
        "notes",
        "item__name",
        "item__cabin__name",
    ]
