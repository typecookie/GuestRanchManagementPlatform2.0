from django import forms
from .models import Horse, Pasture, Saddle, SaddleMaintenanceLog, MedicalRecord, MedicalCareStep

class PastureForm(forms.ModelForm):
    class Meta:
        model = Pasture
        fields = ['name', 'description', 'display_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. North Pasture'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Acreage, water access, terrain notes...'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
        }

class HorseForm(forms.ModelForm):
    class Meta:
        model = Horse
        fields = [
            'name', 'breed', 'color', 'birth_year', 
            'gender', 'status', 'pasture', 'notes', 'medical_notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Spirit'}),
            'breed': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Quarter Horse'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Buckskin'}),
            'birth_year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'YYYY'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'pasture': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'medical_notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pasture'].empty_label = "Unassigned / Barn"

class SaddleForm(forms.ModelForm):
    class Meta:
        model = Saddle
        fields = [
            'saddle_number', 'rack_number', 'seat_size', 
            'min_stirrup_length', 'max_stirrup_length', 
            'purchase_date', 'condition', 'status', 
            'out_of_service_location', 'notes'
        ]
        widgets = {
            'saddle_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. S-101'}),
            'rack_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Rack 5'}),
            'seat_size': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'min_stirrup_length': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_stirrup_length': forms.NumberInput(attrs={'class': 'form-control'}),
            'purchase_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'out_of_service_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Leather Shop'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }

class SaddleMaintenanceLogForm(forms.ModelForm):
    class Meta:
        model = SaddleMaintenanceLog
        fields = ['date', 'description', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'What maintenance was performed?'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Additional notes...'}),
        }

class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = ['diagnosis', 'incident_date', 'resolution_date', 'diagnostics', 'required_care']
        widgets = {
            'diagnosis': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Colic, Hoof Abscess'}),
            'incident_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'resolution_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'diagnostics': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'required_care': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }

class MedicalCareStepForm(forms.ModelForm):
    class Meta:
        model = MedicalCareStep
        fields = ['date', 'description', 'status_update']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'What care was provided?'}),
            'status_update': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Improved, Stable, Needs observation'}),
        }
