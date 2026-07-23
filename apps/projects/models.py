from django.db import models
from django.utils import timezone
from django.conf import settings


class Project(models.Model):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        APPROVED = "approved", "Approved"
        TURNED_BACK = "turned_back", "Turned Back"
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In Progress"
        FINISHED = "finished", "Finished"

    name = models.CharField(max_length=255)
    cabin = models.ForeignKey('cabins.Cabin', on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    vehicle = models.ForeignKey('vehicles.Vehicle', on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    
    equipment = models.TextField(blank=True, help_text="Equipment needed for the project")
    parts = models.TextField(blank=True, help_text="Parts needed for the project")
    
    proposed_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    actual_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    notes = models.TextField(blank=True)
    
    project_owner = models.CharField(max_length=255, blank=True, default="")
    primary_worker = models.CharField(max_length=255, blank=True, default="")
    other_workers = models.TextField(blank=True, default="", help_text="Comma-separated list of other workers")
    
    show_in_ranch_operations = models.BooleanField(default=False, verbose_name="Show in Ranch Operations")
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROPOSED
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.pk:
            old_status = Project.objects.get(pk=self.pk).status
            if old_status != self.status:
                ProjectHistory.objects.create(
                    project=self,
                    from_status=old_status,
                    to_status=self.status
                )
        super().save(*args, **kwargs)


class ProjectHistory(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='history')
    from_status = models.CharField(max_length=20, choices=Project.Status.choices)
    to_status = models.CharField(max_length=20, choices=Project.Status.choices)
    moved_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-moved_at']
        verbose_name_plural = "Project histories"

    def __str__(self):
        return f"{self.project.name}: {self.from_status} -> {self.to_status} at {self.moved_at}"
