from django import forms
from .models import Employee, PositionHistory, Interview

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['user', 'first_name', 'last_name', 'status', 'status_reason', 'performance_notes', 'current_position']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'status_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'performance_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'current_position': forms.TextInput(attrs={'class': 'form-control', 'list': 'positions-datalist'}),
        }

class PositionHistoryForm(forms.ModelForm):
    class Meta:
        model = PositionHistory
        fields = ['position', 'start_date', 'end_date', 'notes']
        widgets = {
            'position': forms.TextInput(attrs={'class': 'form-control', 'list': 'positions-datalist'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class InterviewForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = ['date', 'notes', 'status', 'is_interviewing', 'offered_position', 'follow_up_reason']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_interviewing': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'offered_position': forms.TextInput(attrs={'class': 'form-control', 'list': 'positions-datalist'}),
            'follow_up_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
