from django import forms
from .models import Project
from apps.cabins.models import Cabin
from apps.vehicles.models import Vehicle

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'name', 'cabin', 'vehicle', 'equipment', 'parts', 
            'proposed_cost', 'actual_cost', 'notes', 
            'project_owner', 'primary_worker', 'other_workers', 
            'show_in_ranch_operations'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'cabin': forms.Select(attrs={'class': 'form-control'}),
            'vehicle': forms.Select(attrs={'class': 'form-control'}),
            'equipment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'parts': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'proposed_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'actual_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'project_owner': forms.TextInput(attrs={'class': 'form-control'}),
            'primary_worker': forms.TextInput(attrs={'class': 'form-control'}),
            'other_workers': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'show_in_ranch_operations': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
