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
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='interviews')
    date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=Status.choices)
    
    # Sub-status
    is_interviewing = models.BooleanField(default=False, verbose_name="Interviewing")
    
    # Conditional fields
    offered_position = models.CharField(max_length=255, blank=True, help_text="Position offered if job offered")
    follow_up_reason = models.TextField(blank=True, help_text="Reason why follow-up is required")
    
    def __str__(self):
        return f"Interview for {self.employee} on {self.date} ({self.get_status_display()})"

    class Meta:
        ordering = ['-date']
