from django import forms
from django.db.models import Q
from django.urls import reverse_lazy
from .models import Project
from apps.cabins.models import Cabin, CabinInventoryItem
from apps.vehicles.models import Vehicle
from apps.employees.models import Employee
from apps.contractors.models import Contractor

class ProjectForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter to only show active employees for new assignments
        # But include already assigned employees even if they are no longer active
        active_employees = Employee.objects.filter(status='active')
        
        if self.instance.pk:
            # For existing project, include currently assigned even if inactive
            assigned_ids = list(self.instance.assigned_employees.values_list('pk', flat=True))
            if self.instance.project_lead_id:
                assigned_ids.append(self.instance.project_lead_id)
            
            self.fields['project_lead'].queryset = Employee.objects.filter(
                Q(status='active') | Q(pk=self.instance.project_lead_id)
            )
            self.fields['assigned_employees'].queryset = Employee.objects.filter(
                Q(status='active') | Q(pk__in=assigned_ids)
            )
        else:
            self.fields['project_lead'].queryset = active_employees
            self.fields['assigned_employees'].queryset = active_employees

        # Populate cabin inventory items
        self.fields['cabin_item'].queryset = CabinInventoryItem.objects.select_related('cabin').all()
        self.fields['cabin_item'].required = False
        self.fields['cabin'].required = False
        self.fields['vehicle'].required = False
        self.fields['contractor'].required = False

    class Meta:
        model = Project
        fields = [
            'name', 'cabin', 'cabin_item', 'vehicle', 'contractor', 'equipment', 'parts', 
            'proposed_cost', 'actual_cost', 'notes', 
            'project_lead', 'assigned_employees',
            'project_owner', 'primary_worker', 'other_workers', 
            'show_in_ranch_operations'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'cabin': forms.Select(attrs={'class': 'form-control'}),
            'cabin_item': forms.Select(attrs={'class': 'form-control'}),
            'vehicle': forms.Select(attrs={'class': 'form-control'}),
            'contractor': forms.Select(attrs={
                'class': 'form-select js-searchable-select',
                'data-placeholder': 'Search distributor or contractor...',
                'data-quick-add-url': reverse_lazy('contractors:quick_add_contractor')
            }),
            'equipment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'parts': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'proposed_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'actual_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'project_lead': forms.Select(attrs={
                'class': 'form-select js-searchable-select',
                'data-placeholder': 'Search by name or position...',
                'data-quick-add-url': reverse_lazy('employees:quick_add_employee')
            }),
            'assigned_employees': forms.SelectMultiple(attrs={'class': 'form-control', 'style': 'height: 120px;'}),
            'project_owner': forms.TextInput(attrs={'class': 'form-control'}),
            'primary_worker': forms.TextInput(attrs={'class': 'form-control'}),
            'other_workers': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'show_in_ranch_operations': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
