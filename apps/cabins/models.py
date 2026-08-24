from django.db import models
from django.utils import timezone


class Cabin(models.Model):
    class CabinStatus(models.TextChoices):
        AVAILABLE = "available", "Available"
        OCCUPIED = "occupied", "Occupied"
        MAINTENANCE = "maintenance", "Maintenance"
        OUT_OF_SERVICE = "out_of_service", "Out of Service"
        INACTIVE = "inactive", "Inactive"

    class HousekeepingStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        CLEAN = "clean", "Clean"
        DIRTY = "dirty", "Dirty"
        INSPECTED = "inspected", "Inspected"
        NEEDS_ATTENTION = "needs_attention", "Needs Attention"

    name = models.CharField(max_length=100)
    cabin_number = models.CharField(max_length=30, blank=True)

    capacity = models.PositiveIntegerField(default=1)
    bed_configuration = models.CharField(
        max_length=255,
        blank=True,
        help_text="Example: 1 queen, 2 twins, sleeper sofa",
    )

    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=30,
        choices=CabinStatus.choices,
        default=CabinStatus.AVAILABLE,
    )
    housekeeping_status = models.CharField(
        max_length=30,
        choices=HousekeepingStatus.choices,
        default=HousekeepingStatus.UNKNOWN,
    )

    notes = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Controls display order in cabin lists and reservation grids.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["cabin_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["housekeeping_status"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        if self.cabin_number:
            return f"{self.name} ({self.cabin_number})"

        return self.name


class CabinInventoryItem(models.Model):
    class Category(models.TextChoices):
        APPLIANCE = "appliance", "Appliance"
        FURNITURE = "furniture", "Furniture"
        ELECTRONICS = "electronics", "Electronics"
        FIXTURE = "fixture", "Fixture & Plumbing"
        AMENITY = "amenity", "Amenity & Linens"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        OPERATIONAL = "operational", "Operational / In Service"
        MAINTENANCE = "maintenance", "Needs Maintenance"
        OUT_OF_SERVICE = "out_of_service", "Out of Service"
        REPLACED = "replaced", "Replaced / Disposed"

    class Condition(models.TextChoices):
        EXCELLENT = "excellent", "Excellent"
        GOOD = "good", "Good"
        FAIR = "fair", "Fair"
        POOR = "poor", "Poor"
        BROKEN = "broken", "Broken / Needs Repair"

    cabin = models.ForeignKey(Cabin, on_delete=models.CASCADE, related_name="inventory_items")
    name = models.CharField(max_length=150, help_text="e.g. Washing Machine, Refrigerator, King Bed")
    category = models.CharField(max_length=50, choices=Category.choices, default=Category.APPLIANCE)
    brand = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    location_in_cabin = models.CharField(max_length=100, blank=True, help_text="e.g. Laundry Room, Kitchen, Master Bedroom")
    installed_date = models.DateField(null=True, blank=True)
    warranty_expiration = models.DateField(null=True, blank=True)
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.GOOD)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPERATIONAL)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.cabin.name} - {self.name}"


class CabinInventoryMaintenanceLog(models.Model):
    class StatusUpdate(models.TextChoices):
        OPERATIONAL = "operational", "Operational / In Service"
        NEEDS_FOLLOW_UP = "needs_follow_up", "Needs Follow-up"
        OUT_OF_SERVICE = "out_of_service", "Out of Service"

    item = models.ForeignKey(CabinInventoryItem, on_delete=models.CASCADE, related_name="maintenance_logs")
    date = models.DateField(default=timezone.now)
    title = models.CharField(max_length=255, help_text="e.g. Filter cleaning, Drum belt repair, Annual inspection")
    performed_by = models.CharField(max_length=150, blank=True, help_text="Staff member, technician or contractor")
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    work_performed = models.TextField(help_text="Details of maintenance/repairs performed")
    status_update = models.CharField(max_length=20, choices=StatusUpdate.choices, default=StatusUpdate.OPERATIONAL)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.date}: {self.item.name} - {self.title}"
