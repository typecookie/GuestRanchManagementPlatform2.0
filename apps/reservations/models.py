from datetime import time

from django.core.exceptions import ValidationError
from django.db import models

from apps.cabins.models import Cabin
from apps.clients.models import Client, Household, TravelGroup


class Reservation(models.Model):
    class ReservationType(models.TextChoices):
        GUEST_STAY = "guest_stay", "Guest Stay"
        SHORT_STAY = "short_stay", "Short Stay"
        WORK_CREW = "work_crew", "Work Crew"
        FARRIER = "farrier", "Farrier"
        MAINTENANCE_BLOCK = "maintenance_block", "Maintenance Block"
        OWNER_STAFF = "owner_staff", "Owner / Staff Use"
        OTHER = "other", "Other"

    class ReservationStatus(models.TextChoices):
        INQUIRY = "inquiry", "Inquiry"
        PENCILED = "penciled", "Penciled In"
        CONFIRMED = "confirmed", "Confirmed"
        CHECKED_IN = "checked_in", "Checked In"
        CHECKED_OUT = "checked_out", "Checked Out"
        CANCELLED = "cancelled", "Cancelled"
        BLOCKED = "blocked", "Blocked"

    reservation_name = models.CharField(max_length=150)

    reservation_type = models.CharField(
        max_length=40,
        choices=ReservationType.choices,
        default=ReservationType.GUEST_STAY,
    )
    status = models.CharField(
        max_length=30,
        choices=ReservationStatus.choices,
        default=ReservationStatus.PENCILED,
    )

    primary_contact = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations_as_primary_contact",
    )
    household = models.ForeignKey(
        Household,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations",
    )
    travel_group = models.ForeignKey(
        TravelGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations",
    )

    arrival_date = models.DateField()
    departure_date = models.DateField()

    check_in_time = models.TimeField(default=time(15, 0))
    check_out_time = models.TimeField(default=time(10, 0))

    adult_count = models.PositiveIntegerField(default=0)
    child_count = models.PositiveIntegerField(default=0)
    guest_count = models.PositiveIntegerField(
        default=0,
        help_text="Optional total guest count. Can be adult + child count or manually adjusted.",
    )

    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["arrival_date", "reservation_name"]
        indexes = [
            models.Index(fields=["arrival_date"]),
            models.Index(fields=["departure_date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["reservation_type"]),
            models.Index(fields=["primary_contact"]),
            models.Index(fields=["household"]),
            models.Index(fields=["travel_group"]),
        ]

    def __str__(self):
        return f"{self.reservation_name} ({self.arrival_date} - {self.departure_date})"

    @property
    def calculated_guest_count(self):
        return self.adult_count + self.child_count

    @property
    def display_guest_count(self):
        if self.guest_count:
            return self.guest_count

        return self.calculated_guest_count

    def clean(self):
        if self.arrival_date and self.departure_date:
            if self.departure_date <= self.arrival_date:
                raise ValidationError("Departure date must be after arrival date.")


class ReservationCabin(models.Model):
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="cabin_assignments",
    )
    cabin = models.ForeignKey(
        Cabin,
        on_delete=models.PROTECT,
        related_name="reservation_assignments",
    )

    arrival_date = models.DateField()
    departure_date = models.DateField()

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["arrival_date", "cabin__sort_order", "cabin__name"]
        indexes = [
            models.Index(fields=["arrival_date"]),
            models.Index(fields=["departure_date"]),
            models.Index(fields=["cabin"]),
            models.Index(fields=["reservation"]),
        ]

    def __str__(self):
        return f"{self.cabin} - {self.reservation}"

    def clean(self):
        if self.arrival_date and self.departure_date:
            if self.departure_date <= self.arrival_date:
                raise ValidationError("Cabin departure date must be after arrival date.")

        if self.reservation_id:
            if self.arrival_date and self.reservation.arrival_date:
                if self.arrival_date < self.reservation.arrival_date:
                    raise ValidationError("Cabin arrival date cannot be before reservation arrival date.")

            if self.departure_date and self.reservation.departure_date:
                if self.departure_date > self.reservation.departure_date:
                    raise ValidationError("Cabin departure date cannot be after reservation departure date.")

        if self.cabin_id and self.arrival_date and self.departure_date:
            overlapping_assignments = ReservationCabin.objects.filter(
                cabin=self.cabin,
                arrival_date__lt=self.departure_date,
                departure_date__gt=self.arrival_date,
            ).exclude(
                reservation__status=Reservation.ReservationStatus.CANCELLED,
            )

            if self.pk:
                overlapping_assignments = overlapping_assignments.exclude(pk=self.pk)

            if overlapping_assignments.exists():
                raise ValidationError("This cabin is already assigned during the selected date range.")


class ReservationGuest(models.Model):
    class RidingExperience(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        NO_EXPERIENCE = "no_experience", "No Experience"
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"
        NON_RIDER = "non_rider", "Non-Rider"

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="guests",
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="reservation_guest_records",
    )
    cabin = models.ForeignKey(
        Cabin,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservation_guests",
        help_text="Cabin this guest is staying in for this reservation.",
    )

    age_at_stay = models.PositiveIntegerField(null=True, blank=True)
    height = models.CharField(
        max_length=50,
        blank=True,
        help_text="Example: 5'8\" or 68 inches",
    )
    weight = models.CharField(
        max_length=50,
        blank=True,
        help_text="Example: 150 lbs",
    )

    riding_experience = models.CharField(
        max_length=30,
        choices=RidingExperience.choices,
        default=RidingExperience.UNKNOWN,
    )

    allergies = models.TextField(blank=True)
    food_requests = models.TextField(blank=True)
    medical_notes = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    is_riding = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["client__last_name", "client__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["reservation", "client"],
                name="unique_client_per_reservation_guest",
            )
        ]
        indexes = [
            models.Index(fields=["reservation"]),
            models.Index(fields=["client"]),
            models.Index(fields=["cabin"]),
            models.Index(fields=["riding_experience"]),
        ]

    def __str__(self):
        return f"{self.client} - {self.reservation}"
