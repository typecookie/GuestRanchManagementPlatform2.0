from django import forms
from .models import Employee, PositionHistory, Interview, StaffSchedule
from apps.reservations.models import OperatingSeason

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
        fields = ['employee', 'candidate_name', 'candidate_email', 'candidate_phone', 'date', 'status', 'is_interviewing', 'offered_position', 'follow_up_reason', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'candidate_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Jane Doe'}),
            'candidate_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'candidate@example.com'}),
            'candidate_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(555) 123-4567'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_interviewing': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'offered_position': forms.TextInput(attrs={'class': 'form-control', 'list': 'positions-datalist'}),
            'follow_up_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        self.target_employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
        self.fields['employee'].required = False
        self.fields['employee'].empty_label = "-- None (Candidate / Not Yet Hired) --"
        
        # If logging for a specific employee
        if self.target_employee:
            self.fields['employee'].initial = self.target_employee
            self.fields['employee'].widget = forms.HiddenInput()
            self.fields['candidate_name'].widget = forms.HiddenInput()
            self.fields['candidate_email'].widget = forms.HiddenInput()
            self.fields['candidate_phone'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        employee = cleaned_data.get('employee') or self.target_employee
        candidate_name = cleaned_data.get('candidate_name')
        
        if not employee and not (candidate_name and candidate_name.strip()):
            raise forms.ValidationError("Please select an existing employee or enter a candidate name.")
        
        # If employee is selected, clear candidate name
        if employee:
            cleaned_data['candidate_name'] = ''
            
        return cleaned_data


class StaffScheduleForm(forms.ModelForm):
    class Meta:
        model = StaffSchedule
        fields = [
            'season',
            'position',
            'employee',
            'placeholder_name',
            'is_placeholder',
            'status',
            'start_date',
            'end_date',
            'notes',
        ]
        widgets = {
            'season': forms.Select(attrs={'class': 'form-select'}),
            'position': forms.TextInput(attrs={'class': 'form-control', 'list': 'positions-datalist', 'placeholder': 'e.g. Wrangler, Lead Chef, Housekeeping'}),
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'placeholder_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Placeholder Wrangler #1 or Candidate Name'}),
            'is_placeholder': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional assignment details or notes'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['season'].queryset = OperatingSeason.objects.all().order_by('-start_date')
        self.fields['season'].empty_label = "-- Select Operating Season (Optional) --"
        self.fields['season'].required = False
        
        self.fields['employee'].queryset = Employee.objects.all().order_by('last_name', 'first_name')
        self.fields['employee'].required = False
        self.fields['employee'].empty_label = "-- None (Placeholder / Unconfirmed Person) --"

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        employee = cleaned_data.get('employee')
        placeholder_name = cleaned_data.get('placeholder_name')
        is_placeholder = cleaned_data.get('is_placeholder')
        status = cleaned_data.get('status')
        position = cleaned_data.get('position')

        if start_date and end_date and start_date > end_date:
            self.add_error('end_date', "End date cannot be earlier than start date.")

        if not employee:
            cleaned_data['is_placeholder'] = True
            if not placeholder_name or not placeholder_name.strip():
                if position:
                    cleaned_data['placeholder_name'] = f"Placeholder {position.strip()}"
                else:
                    cleaned_data['placeholder_name'] = "Unassigned Placeholder"
            if status == StaffSchedule.Status.CONFIRMED:
                cleaned_data['status'] = StaffSchedule.Status.UNCONFIRMED
        else:
            if not is_placeholder:
                cleaned_data['placeholder_name'] = ''
                if status == StaffSchedule.Status.UNCONFIRMED:
                    cleaned_data['status'] = StaffSchedule.Status.CONFIRMED

        return cleaned_data


class StaffScheduleLinkEmployeeForm(forms.Form):
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.all().order_by('last_name', 'first_name'),
        required=True,
        empty_label="-- Select Employee to Link --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=StaffSchedule.Status.choices,
        initial=StaffSchedule.Status.CONFIRMED,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional update notes'})
    )
