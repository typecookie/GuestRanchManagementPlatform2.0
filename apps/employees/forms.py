from django import forms
from .models import Employee, PositionHistory, Interview, StaffSchedule, Department, Position, SeasonPositionTarget
from apps.reservations.models import OperatingSeason

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'code', 'description', 'display_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Barn, Kitchen, Housekeeping'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. barn, kitchen (optional short key)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Department purpose and scope...'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ['department', 'title', 'is_head', 'default_target_count', 'display_order', 'description']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Head Wrangler, Wrangler, Sous Chef'}),
            'is_head': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'default_target_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Role description or duties...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.all().order_by('display_order', 'name')
        self.fields['department'].empty_label = "-- Select Department --"


class SeasonPositionTargetForm(forms.ModelForm):
    class Meta:
        model = SeasonPositionTarget
        fields = ['department', 'position', 'custom_position_title', 'target_count', 'notes']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'position': forms.Select(attrs={'class': 'form-select'}),
            'custom_position_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Trail Guide / Wrangler'}),
            'target_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional requirement details'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.all().order_by('display_order', 'name')
        self.fields['department'].empty_label = "-- Select Department (Optional) --"
        self.fields['department'].required = False

        self.fields['position'].queryset = Position.objects.select_related('department').order_by('department__display_order', 'display_order', 'title')
        self.fields['position'].empty_label = "-- Select Master Position (Optional) --"
        self.fields['position'].required = False

    def clean(self):
        cleaned_data = super().clean()
        position = cleaned_data.get('position')
        custom_title = cleaned_data.get('custom_position_title')
        department = cleaned_data.get('department')

        if not position and not (custom_title and custom_title.strip()):
            raise forms.ValidationError("Please select a master position or specify a custom position title.")

        if position and not department:
            cleaned_data['department'] = position.department

        return cleaned_data


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
            'department',
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
            'department': forms.Select(attrs={'class': 'form-select'}),
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
        
        self.fields['department'].queryset = Department.objects.all().order_by('display_order', 'name')
        self.fields['department'].empty_label = "-- Select Department (Optional / Auto-resolved) --"
        self.fields['department'].required = False

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
            if not placeholder_name or not placeholder_name.strip():
                if position:
                    cleaned_data['placeholder_name'] = f"Placeholder {position.strip()}"
                else:
                    cleaned_data['placeholder_name'] = "Unassigned Staff"
        else:
            if not is_placeholder:
                cleaned_data['placeholder_name'] = ''

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
