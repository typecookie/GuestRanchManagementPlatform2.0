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
    department = models.ForeignKey(
        'Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_schedules',
        help_text="Department for this position assignment"
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
    def is_tentative(self):
        return self.status == self.Status.TENTATIVE

    @property
    def is_confirmed(self):
        return self.status == self.Status.CONFIRMED and not self.is_placeholder

    @property
    def is_unconfirmed_entry(self):
        return bool(self.is_placeholder or self.status == self.Status.UNCONFIRMED)

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

    def save(self, *args, **kwargs):
        if not self.department and self.position:
            # Try to resolve department from Position model
            matched_pos = Position.objects.filter(title__iexact=self.position.strip()).first()
            if matched_pos and matched_pos.department:
                self.department = matched_pos.department
        super().save(*args, **kwargs)

    def __str__(self):
        name = self.staff_name
        return f"{self.position}: {name} ({self.start_date} – {self.end_date})"

    class Meta:
        ordering = ['position', 'start_date', 'employee__last_name']


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Department name (e.g. Barn, Kitchen, Housekeeping)")
    code = models.CharField(max_length=50, blank=True, help_text="Department identifier or slug (e.g. barn, kitchen)")
    description = models.TextField(blank=True, help_text="Department description or responsibilities")
    display_order = models.PositiveIntegerField(default=0, help_text="Display sorting order")
    is_default = models.BooleanField(default=False, help_text="Whether this is a standard ranch department")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['display_order', 'name']


class Position(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='positions')
    title = models.CharField(max_length=255, help_text="Position title (e.g. Head Wrangler, Prep Cook)")
    is_head = models.BooleanField(default=False, help_text="Department head or supervisory leadership role")
    default_target_count = models.PositiveIntegerField(default=1, help_text="Standard season target headcount for this position")
    display_order = models.PositiveIntegerField(default=0, help_text="Display ordering within department")
    description = models.TextField(blank=True, help_text="Role responsibilities and requirements")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.department.name})"

    class Meta:
        ordering = ['department__display_order', 'display_order', 'title']
        unique_together = [('department', 'title')]


class SeasonPositionTarget(models.Model):
    season = models.ForeignKey(
        'reservations.OperatingSeason',
        on_delete=models.CASCADE,
        related_name='position_targets',
        help_text="Operating season for this position headcount target"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='season_targets',
        help_text="Department for this position"
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='season_targets',
        help_text="Master position definition (optional)"
    )
    custom_position_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Custom position title if not linked to a master position"
    )
    target_count = models.PositiveIntegerField(
        default=1,
        help_text="Planned headcount for this position during this season"
    )
    notes = models.TextField(blank=True, help_text="Notes regarding this position requirement")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def position_title(self):
        if self.position:
            return self.position.title
        return self.custom_position_title or "Unassigned Position"

    @property
    def department_name(self):
        if self.department:
            return self.department.name
        if self.position and self.position.department:
            return self.position.department.name
        return "General / Unassigned"

    def get_scheduled_count(self):
        title = self.position_title
        return StaffSchedule.objects.filter(season=self.season, position__iexact=title).count()

    def get_confirmed_count(self):
        title = self.position_title
        return StaffSchedule.objects.filter(
            season=self.season,
            position__iexact=title,
            status=StaffSchedule.Status.CONFIRMED,
            is_placeholder=False
        ).count()

    def get_placeholder_count(self):
        title = self.position_title
        return StaffSchedule.objects.filter(
            season=self.season,
            position__iexact=title
        ).filter(
            models.Q(is_placeholder=True) | models.Q(status=StaffSchedule.Status.UNCONFIRMED)
        ).count()

    def get_tentative_count(self):
        title = self.position_title
        return StaffSchedule.objects.filter(
            season=self.season,
            position__iexact=title,
            status=StaffSchedule.Status.TENTATIVE
        ).count()

    def __str__(self):
        return f"{self.season.name}: {self.position_title} (Target: {self.target_count})"

    class Meta:
        ordering = ['department__display_order', 'position__display_order', 'id']
