from datetime import time

from django.core.exceptions import ValidationError
from django.db import models

from apps.cabins.models import Cabin
from apps.clients.models import Client, Household, TravelGroup, calculate_age_at_date


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

    is_driving = models.BooleanField(default=False)
    driving_notes = models.TextField(blank=True)
    is_flying = models.BooleanField(default=False)
    flying_notes = models.TextField(blank=True)

    deposit_request_sent = models.BooleanField(default=False)
    deposit_received = models.BooleanField(default=False)

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
        ordering = ["arrival_date", "cabin__capacity", "cabin__sort_order", "cabin__name"]
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
    horse = models.ForeignKey(
        "horses.Horse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservation_guests",
    )
    saddle = models.ForeignKey(
        "horses.Saddle",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservation_guests",
    )

    age_at_stay = models.PositiveIntegerField(null=True, blank=True)

    allergies = models.TextField(blank=True)
    food_requests = models.TextField(blank=True)
    medical_notes = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    is_riding = models.BooleanField(default=True)
    signed_release = models.BooleanField(default=False)

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
        ]

    def __str__(self):
        return f"{self.client} - {self.reservation}"

    def save(self, *args, **kwargs):
        if self.client_id:
            # If client is marked as non-rider in client profile and record is new, default is_riding to False
            if not self.pk and (not self.client.is_rider or self.client.riding_level == self.RidingExperience.NON_RIDER):
                self.is_riding = False
            if self.age_at_stay is None:
                if self.client.date_of_birth and self.reservation_id and self.reservation.arrival_date:
                    self.age_at_stay = calculate_age_at_date(self.client.date_of_birth, self.reservation.arrival_date)
                elif self.client.effective_age is not None:
                    self.age_at_stay = self.client.effective_age
        super().save(*args, **kwargs)

    @property
    def effective_age(self):
        if self.age_at_stay is not None:
            return self.age_at_stay
        if self.client_id:
            if self.client.date_of_birth and self.reservation_id and self.reservation.arrival_date:
                return calculate_age_at_date(self.client.date_of_birth, self.reservation.arrival_date)
            return self.client.effective_age
        return None

    @property
    def effective_age_at_stay(self):
        return self.effective_age

    @property
    def height(self):
        if self.client_id and self.client.height:
            return self.client.height
        return ""

    @property
    def weight(self):
        if self.client_id and self.client.weight:
            return self.client.weight
        return ""

    @property
    def effective_height(self):
        return self.height

    @property
    def effective_weight(self):
        return self.weight

    @property
    def riding_experience(self):
        if self.client_id and self.client.riding_level:
            return self.client.riding_level
        return self.RidingExperience.UNKNOWN

    @property
    def effective_riding_experience(self):
        return self.riding_experience

    def get_riding_experience_display(self):
        val = self.riding_experience
        for choice_val, choice_label in self.RidingExperience.choices:
            if choice_val == val:
                return str(choice_label)
        return val.replace("_", " ").title() if val else ""

    @property
    def sex(self):
        if self.client_id and self.client.sex:
            return self.client.sex
        return ""

    @property
    def effective_sex(self):
        return self.sex

    def get_sex_display(self):
        if self.client_id and self.client:
            return self.client.get_sex_display()
        return ""

    @property
    def years_count(self):
        # 1. Direct Client explicit years_return
        if self.client_id and self.client.years_return is not None:
            return self.client.years_return

        # 2. Check Household (reservation.household or client membership)
        household = None
        if self.reservation_id and self.reservation.household_id:
            household = self.reservation.household
        elif self.client_id:
            membership = self.client.household_memberships.select_related("household").first()
            if membership:
                household = membership.household

        if household and household.years_return is not None:
            return household.years_return

        # 3. Check Travel Group (reservation.travel_group, client tg membership, or household tg membership)
        travel_group = None
        if self.reservation_id and self.reservation.travel_group_id:
            travel_group = self.reservation.travel_group
        elif self.client_id:
            tg_member = self.client.travel_group_memberships.select_related("travel_group").first()
            if tg_member:
                travel_group = tg_member.travel_group
            elif household:
                hh_tg_member = household.travel_group_memberships.select_related("travel_group").first()
                if hh_tg_member:
                    travel_group = hh_tg_member.travel_group

        if travel_group and travel_group.years_return is not None:
            return travel_group.years_return

        # 4. Fallback: Parse notes regex
        import re
        notes_text = f"{self.notes}\n{self.client.general_notes if self.client_id else ''}"
        match = re.search(r"(\d+)(?:st|nd|rd|th)?\s+year", notes_text, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # 5. Fallback: Database prior reservation arrival count
        if self.client_id and self.reservation_id and self.reservation.arrival_date:
            count = ReservationGuest.objects.filter(
                client_id=self.client_id,
                reservation__arrival_date__year__lte=self.reservation.arrival_date.year,
            ).exclude(
                reservation__status=Reservation.ReservationStatus.CANCELLED,
            ).values("reservation__arrival_date__year").distinct().count()
            if count > 0:
                return count

        return 1

    @property
    def years_display(self):
        from apps.clients.models import format_years_ordinal
        return format_years_ordinal(self.years_count)


class ReservationFlight(models.Model):
    class FlightType(models.TextChoices):
        ARRIVAL = "arrival", "Arrival"
        DEPARTURE = "departure", "Departure"

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="flights",
    )
    flight_type = models.CharField(
        max_length=20,
        choices=FlightType.choices,
        default=FlightType.ARRIVAL,
    )
    airport = models.CharField(
        max_length=150,
        blank=True,
        help_text="Airport name or code, e.g. Casper (CPR), Denver (DEN)",
    )
    flight_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Airline and flight number, e.g. UA 4521",
    )
    flight_date = models.DateField(
        null=True,
        blank=True,
        help_text="Flight date",
    )
    flight_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Arrival or departure time",
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional flight notes (e.g. connections, shuttle requests, passenger names)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["airport", "flight_type", "flight_date", "flight_time", "created_at"]
        indexes = [
            models.Index(fields=["reservation"]),
            models.Index(fields=["airport"]),
            models.Index(fields=["flight_type"]),
            models.Index(fields=["flight_date"]),
        ]

    def __str__(self):
        type_str = self.get_flight_type_display()
        num_str = f" #{self.flight_number}" if self.flight_number else ""
        airport_str = f" at {self.airport}" if self.airport else ""
        return f"{type_str} Flight{num_str}{airport_str} ({self.reservation})"


class OperatingSeason(models.Model):
    name = models.CharField(
        max_length=100,
        help_text="Name or label for the operating season (e.g. 'Summer 2026', 'Main Season').",
    )
    start_date = models.DateField(
        help_text="Opening date for the ranch.",
    )
    end_date = models.DateField(
        help_text="Closing date for the ranch.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this operating season is currently active.",
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional notes or details about this operating season.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_date", "name"]
        verbose_name = "Operating Season"
        verbose_name_plural = "Operating Seasons"
        indexes = [
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.start_date.strftime('%b %d, %Y')} – {self.end_date.strftime('%b %d, %Y')})"

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError({"end_date": "End date must be after start date."})

    def contains_date(self, target_date):
        return self.start_date <= target_date <= self.end_date

    def overlaps_week(self, week_start, week_end):
        return self.start_date < week_end and self.end_date >= week_start

    def is_prior(self, reference_date=None):
        """
        A season is considered prior as soon as its last day open passes (reference_date > end_date).
        """
        from datetime import date
        if reference_date is None:
            reference_date = date.today()
        return reference_date > self.end_date

    def is_current(self, reference_date=None):
        """
        A season is current if reference_date is between start_date and end_date (inclusive).
        """
        from datetime import date
        if reference_date is None:
            reference_date = date.today()
        return self.start_date <= reference_date <= self.end_date

    def is_upcoming(self, reference_date=None):
        """
        A season is upcoming if reference_date is before start_date.
        """
        from datetime import date
        if reference_date is None:
            reference_date = date.today()
        return reference_date < self.start_date

    def status_label(self, reference_date=None):
        if self.is_current(reference_date):
            return "Current Season"
        if self.is_prior(reference_date):
            return "Prior Season"
        return "Next Season" if self.is_upcoming(reference_date) else "Upcoming Season"

    @property
    def duration_days(self):
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0

    @property
    def duration_weeks(self):
        return round(self.duration_days / 7, 1)
