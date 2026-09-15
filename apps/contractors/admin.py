from django.contrib import admin
from .models import Contractor


@admin.register(Contractor)
class ContractorAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'contact_name', 'phone', 'city', 'state', 'is_active')
    list_filter = ('category', 'is_active', 'state')
    search_fields = ('name', 'contact_name', 'phone', 'email', 'city')
