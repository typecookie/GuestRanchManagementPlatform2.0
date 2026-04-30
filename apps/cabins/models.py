from django.db import models


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
