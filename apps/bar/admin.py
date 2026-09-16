from django.contrib import admin
from .models import BarInventoryItem, BarItemTag


@admin.register(BarItemTag)
class BarItemTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)


@admin.register(BarInventoryItem)
class BarInventoryItemAdmin(admin.ModelAdmin):
    list_display = ('stock_number', 'description', 'category', 'pricing_method', 'beverage_class', 'tag', 'on_hand', 'minimum_on_hand', 'single_price', 'case_price', 'sale_price', 'total_value', 'distributor', 'is_active')
    list_filter = ('pricing_method', 'beverage_class', 'category', 'tag', 'is_active', 'distributor', 'location')
    search_fields = ('stock_number', 'description', 'tag__name', 'distributor__name', 'location')
