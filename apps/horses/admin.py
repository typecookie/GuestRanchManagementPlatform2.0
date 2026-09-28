from django.contrib import admin
from .models import Horse, Pasture, Saddle, SaddleMaintenanceLog, MedicalRecord, MedicalCareStep

@admin.register(Pasture)
class PastureAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_order', 'get_horse_count', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('display_order', 'name')

    def get_horse_count(self, obj):
        return obj.horse_count
    get_horse_count.short_description = 'Horses'

class MedicalCareStepInline(admin.TabularInline):
    model = MedicalCareStep
    extra = 1

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('horse', 'incident_date', 'resolution_date')
    list_filter = ('horse', 'incident_date')
    inlines = [MedicalCareStepInline]

class MedicalRecordInline(admin.StackedInline):
    model = MedicalRecord
    extra = 0
    show_change_link = True

@admin.register(Horse)
class HorseAdmin(admin.ModelAdmin):
    list_display = ('name', 'breed', 'gender', 'status', 'pasture')
    list_filter = ('status', 'gender', 'pasture')
    search_fields = ('name', 'breed')
    inlines = [MedicalRecordInline]
