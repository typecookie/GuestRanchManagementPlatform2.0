from django.db import models

class Vehicle(models.Model):
    class VehicleType(models.TextChoices):
        TRUCK = "truck", "Truck"
        SUV = "suv", "SUV"
        VAN = "van", "Van"
        UTV = "utv", "UTV/ATV"
        TRACTOR = "tractor", "Tractor"
        OTHER = "other", "Other"

    name = models.CharField(max_length=100)
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices, default=VehicleType.TRUCK)
    make = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    license_plate = models.CharField(max_length=20, blank=True)
    vin = models.CharField(max_length=50, blank=True)
    
    notes = models.TextField(blank=True)
    maintenance_notes = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_vehicle_type_display()})"

class MaintenanceRecord(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='maintenance_records')
    issue = models.CharField(max_length=255, verbose_name="Issue/Service Type", default="General Maintenance")
    start_date = models.DateField(verbose_name="Date Started")
    completion_date = models.DateField(null=True, blank=True, verbose_name="Date Completed")
    diagnostics = models.TextField(help_text="Diagnostics/Inspection results")
    required_maintenance = models.TextField(help_text="Required repairs/service")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.vehicle.name} - {self.issue} ({self.start_date})"

class MaintenanceStep(models.Model):
    maintenance_record = models.ForeignKey(MaintenanceRecord, on_delete=models.CASCADE, related_name='steps')
    date = models.DateField()
    description = models.TextField(help_text="Details of work performed")
    status_update = models.CharField(max_length=255, blank=True, help_text="Update on the vehicle's status")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "created_at"]

    def __str__(self):
        return f"{self.date}: {self.description[:50]}"
