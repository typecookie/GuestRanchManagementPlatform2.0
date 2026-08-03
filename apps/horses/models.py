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

class Saddle(models.Model):
    class Status(models.TextChoices):
        IN_SERVICE = "in_service", "In Service"
        OUT_OF_SERVICE = "out_of_service", "Out of Service"

    saddle_number = models.CharField(max_length=50, unique=True, verbose_name="Saddle Identifier")
    rack_number = models.CharField(max_length=50, blank=True)
    seat_size = models.DecimalField(max_digits=4, decimal_places=1, help_text="Seat size in inches (e.g. 14.5)")
    min_stirrup_length = models.PositiveIntegerField(help_text="In inches")
    max_stirrup_length = models.PositiveIntegerField(help_text="In inches")
    purchase_date = models.DateField(null=True, blank=True)
    condition = models.PositiveIntegerField(
        choices=[(1, "1 (Red)"), (2, "2"), (3, "3"), (4, "4"), (5, "5 (Green)")],
        default=5
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.IN_SERVICE
    )
    out_of_service_location = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Location if out of service (e.g. Leather Shop)"
    )
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "rack_number", "saddle_number"]

    def __str__(self):
        if self.rack_number:
            res = f"Rack {self.rack_number}"
        else:
            res = f"Saddle {self.saddle_number}"
        
        if self.status == self.Status.OUT_OF_SERVICE:
            res += " [OUT OF SERVICE]"
        return res

class SaddleMaintenanceLog(models.Model):
    saddle = models.ForeignKey(Saddle, on_delete=models.CASCADE, related_name='maintenance_logs')
    date = models.DateField()
    description = models.TextField()
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.date}: {self.saddle.saddle_number}"

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
