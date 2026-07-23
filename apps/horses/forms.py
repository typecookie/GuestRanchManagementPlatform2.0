from django import forms
from .models import Horse, MedicalRecord, MedicalCareStep

class HorseForm(forms.ModelForm):
    class Meta:
        model = Horse
        fields = [
            'name', 'breed', 'color', 'birth_year', 
            'gender', 'status', 'notes', 'medical_notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Spirit'}),
            'breed': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Quarter Horse'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Buckskin'}),
            'birth_year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'YYYY'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'medical_notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
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
