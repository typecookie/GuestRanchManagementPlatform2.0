from django import forms
from .models import Vehicle, MaintenanceRecord, MaintenanceStep

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            'name', 'vehicle_type', 'make', 'model', 'year', 
            'license_plate', 'vin', 'notes', 'maintenance_notes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Ranch Truck 1'}),
            'vehicle_type': forms.Select(attrs={'class': 'form-select'}),
            'make': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Ford'}),
            'model': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. F-150'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'YYYY'}),
            'license_plate': forms.TextInput(attrs={'class': 'form-control'}),
            'vin': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'maintenance_notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

class MaintenanceRecordForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRecord
        fields = ['issue', 'start_date', 'completion_date', 'diagnostics', 'required_maintenance']
        widgets = {
            'issue': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Engine Overheating, Routine Oil Change'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'completion_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'diagnostics': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Diagnostics/Inspection results'}),
            'required_maintenance': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Required repairs/service'}),
        }

class MaintenanceStepForm(forms.ModelForm):
    class Meta:
        model = MaintenanceStep
        fields = ['date', 'description', 'status_update']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'What work was performed?'}),
            'status_update': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Parts ordered, Repaired, Pending test drive'}),
        }
