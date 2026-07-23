from django.db import models

class Horse(models.Model):
    class Gender(models.TextChoices):
        GELDING = "gelding", "Gelding"
        MARE = "mare", "Mare"
        STALLION = "stallion", "Stallion"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        RETIRED = "retired", "Retired"
        OUT_OF_SERVICE = "out_of_service", "Out of Service"
        DECEASED = "deceased", "Deceased"

    name = models.CharField(max_length=100)
    breed = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=100, blank=True)
    birth_year = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, default=Gender.GELDING)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    
    notes = models.TextField(blank=True)
    medical_notes = models.TextField(blank=True, help_text="Legacy medical notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class MedicalRecord(models.Model):
    horse = models.ForeignKey(Horse, on_delete=models.CASCADE, related_name='medical_records')
    diagnosis = models.CharField(max_length=255, verbose_name="Sickness/Injury", default="Unknown")
    incident_date = models.DateField(verbose_name="Date of Injury/Sickness")
    resolution_date = models.DateField(null=True, blank=True)
    diagnostics = models.TextField(help_text="Diagnostics used")
    required_care = models.TextField(help_text="Required care")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-incident_date"]

    def __str__(self):
        return f"{self.horse.name} - {self.diagnosis} ({self.incident_date})"

class MedicalCareStep(models.Model):
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='care_steps')
    date = models.DateField()
    description = models.TextField(help_text="Details of care provided")
    status_update = models.CharField(max_length=255, blank=True, help_text="Update on the horse's condition")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "created_at"]

    def __str__(self):
        return f"{self.date}: {self.description[:50]}"
