from django import forms

from .models import Cabin, CabinInventoryItem, CabinInventoryMaintenanceLog


class CabinForm(forms.ModelForm):
    class Meta:
        model = Cabin
        fields = [
            "name",
            "cabin_number",
            "capacity",
            "bed_configuration",
            "description",
            "status",
            "housekeeping_status",
            "notes",
            "is_active",
            "sort_order",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }


class CabinInventoryItemForm(forms.ModelForm):
    class Meta:
        model = CabinInventoryItem
        fields = [
            "name",
            "category",
            "brand",
            "model_number",
            "serial_number",
            "quantity",
            "location_in_cabin",
            "installed_date",
            "warranty_expiration",
            "condition",
            "status",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Washing Machine, Refrigerator"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "brand": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Whirlpool, Samsung"}),
            "model_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. WTW5000DW"}),
            "serial_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. C123456789"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "location_in_cabin": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Laundry Room, Kitchen, Master Bedroom"}),
            "installed_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "warranty_expiration": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "condition": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-textarea", "rows": 3}),
        }


class CabinInventoryMaintenanceLogForm(forms.ModelForm):
    class Meta:
        model = CabinInventoryMaintenanceLog
        fields = [
            "date",
            "title",
            "performed_by",
            "cost",
            "status_update",
            "work_performed",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Drum Belt Replacement, Filter Clean"}),
            "performed_by": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. John Doe / Appliance Repair Co"}),
            "cost": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "0.00"}),
            "status_update": forms.Select(attrs={"class": "form-select"}),
            "work_performed": forms.Textarea(attrs={"class": "form-textarea", "rows": 3, "placeholder": "Describe maintenance/repairs carried out..."}),
            "notes": forms.Textarea(attrs={"class": "form-textarea", "rows": 2, "placeholder": "Additional notes..."}),
        }