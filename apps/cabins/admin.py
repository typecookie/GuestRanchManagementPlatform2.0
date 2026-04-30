from django.contrib import admin

from .models import Cabin


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
