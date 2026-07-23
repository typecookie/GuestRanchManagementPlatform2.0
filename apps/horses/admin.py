from django.contrib import admin
from .models import Horse, MedicalRecord, MedicalCareStep

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
    list_display = ('name', 'breed', 'gender', 'status')
    list_filter = ('status', 'gender')
    search_fields = ('name', 'breed')
    inlines = [MedicalRecordInline]
