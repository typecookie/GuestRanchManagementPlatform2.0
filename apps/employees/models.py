from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Employee(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        TERMINATED = "terminated", "Terminated"
        END_OF_CONTRACT = "end_of_contract", "End of Contract"
        LEFT_EARLY = "left_early", "Left Early"

    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_profile')
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.ACTIVE
    )
    status_reason = models.TextField(blank=True, help_text="Reason for termination, end of contract, or leaving early")
    
    performance_notes = models.TextField(blank=True)
    
    current_position = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.current_position:
            return f"{self.first_name} {self.last_name} ({self.current_position})"
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ['last_name', 'first_name']

class PositionHistory(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='position_history')
    position = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.employee} - {self.position} ({self.start_date})"

    class Meta:
        ordering = ['-start_date']

class Interview(models.Model):
    class Status(models.TextChoices):
        JOB_OFFERED = "job_offered", "Job Offered"
        FOLLOW_UP = "follow_up", "Follow-up Required"
        NOT_RECOMMENDED = "not_recommended", "Not Recommended"
        PROMOTION_RECOMMENDED = "promotion_recommended", "Recommended for Promotion"
        PROMOTION_FOLLOW_UP = "promotion_follow_up", "Promotion Follow-up"
    
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='interviews')
    candidate_name = models.CharField(max_length=255, blank=True, help_text="Candidate name if not yet an employee")
    candidate_email = models.EmailField(blank=True, help_text="Contact email of candidate")
    candidate_phone = models.CharField(max_length=50, blank=True, help_text="Contact phone number of candidate")
    date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=Status.choices)
    
    # Sub-status
    is_interviewing = models.BooleanField(default=False, verbose_name="Interviewing")
    
    # Conditional fields
    offered_position = models.CharField(max_length=255, blank=True, help_text="Position offered if job offered")
    follow_up_reason = models.TextField(blank=True, help_text="Reason why follow-up is required")
    
    @property
    def interviewee_name(self):
        if self.employee:
            return self.employee.full_name
        return self.candidate_name or "Candidate"

    def __str__(self):
        return f"Interview for {self.interviewee_name} on {self.date} ({self.get_status_display()})"

    class Meta:
        ordering = ['-date']


class StaffSchedule(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        UNCONFIRMED = "unconfirmed", "Unconfirmed / Placeholder"
        TENTATIVE = "tentative", "Tentative"

    season = models.ForeignKey(
        'reservations.OperatingSeason',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_schedules',
        help_text="Operating season for this staffing assignment"
    )
    position = models.CharField(
        max_length=255, 
        help_text="Job position / role"
    )
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='staff_schedules',
        help_text="Assigned employee (leave empty for placeholder / unconfirmed)"
    )
    placeholder_name = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Placeholder name for unconfirmed staff or prospective hire"
    )
    is_placeholder = models.BooleanField(
        default=False, 
        verbose_name="Placeholder",
        help_text="Check if this is an unconfirmed or placeholder position"
    )
    status = models.CharField(
        max_length=30, 
        choices=Status.choices, 
        default=Status.CONFIRMED
    )
    start_date = models.DateField(help_text="Staff member starting date")
    end_date = models.DateField(help_text="Staff member ending date")
    notes = models.TextField(blank=True, help_text="Optional assignment or schedule notes")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def staff_name(self):
        if self.employee:
            return self.employee.full_name
        return self.placeholder_name or "Unassigned Position"

    @property
    def is_unconfirmed_entry(self):
        return bool(not self.employee or self.is_placeholder or self.status == self.Status.UNCONFIRMED)

    @property
    def duration_days(self):
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0

    @property
    def duration_weeks(self):
        return round(self.duration_days / 7, 1)

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError({'end_date': "End date cannot be earlier than start date."})

    def __str__(self):
        name = self.staff_name
        return f"{self.position}: {name} ({self.start_date} – {self.end_date})"

    class Meta:
        ordering = ['position', 'start_date', 'employee__last_name']
