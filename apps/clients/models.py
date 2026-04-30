from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Client(models.Model):
    class ClientType(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        ADULT = "adult", "Adult"
        CHILD = "child", "Child"
        TEEN = "teen", "Teen"
        SENIOR = "senior", "Senior"

    class RidingLevel(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        NO_EXPERIENCE = "no_experience", "No Experience"
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"
        NON_RIDER = "non_rider", "Non-Rider"

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    preferred_name = models.CharField(max_length=100, blank=True)

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    alternate_phone = models.CharField(max_length=30, blank=True)

    date_of_birth = models.DateField(null=True, blank=True)

    client_type = models.CharField(
        max_length=20,
        choices=ClientType.choices,
        default=ClientType.UNKNOWN,
    )
    riding_level = models.CharField(
        max_length=30,
        choices=RidingLevel.choices,
        default=RidingLevel.UNKNOWN,
    )

    dietary_notes = models.TextField(blank=True)
    medical_notes = models.TextField(blank=True)
    general_notes = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["email"]),
            models.Index(fields=["phone"]),
        ]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        name_parts = [
            self.first_name,
            self.middle_name,
            self.last_name,
        ]
        return " ".join(part for part in name_parts if part).strip()

    @property
    def display_name(self):
        if self.preferred_name:
            return f"{self.preferred_name} {self.last_name}".strip()

        return self.full_name


class Household(models.Model):
    name = models.CharField(max_length=150)

    primary_contact = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_households",
    )
    billing_contact = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="billing_households",
    )

    address_line_1 = models.CharField(max_length=150, blank=True)
    address_line_2 = models.CharField(max_length=150, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True, default="United States")

    notes = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name


class HouseholdMember(models.Model):
    class Relationship(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        SELF = "self", "Self"
        SPOUSE = "spouse", "Spouse"
        PARTNER = "partner", "Partner"
        PARENT = "parent", "Parent"
        CHILD = "child", "Child"
        SIBLING = "sibling", "Sibling"
        GRANDPARENT = "grandparent", "Grandparent"
        GRANDCHILD = "grandchild", "Grandchild"
        FRIEND = "friend", "Friend"
        GUARDIAN = "guardian", "Guardian"
        OTHER = "other", "Other"

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="household_memberships",
    )

    relationship = models.CharField(
        max_length=30,
        choices=Relationship.choices,
        default=Relationship.UNKNOWN,
    )

    is_primary_contact = models.BooleanField(default=False)
    is_billing_contact = models.BooleanField(default=False)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["household__name", "client__last_name", "client__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["household", "client"],
                name="unique_client_per_household",
            )
        ]

    def __str__(self):
        return f"{self.client} - {self.household}"


class TravelGroup(models.Model):
    class GroupType(models.TextChoices):
        FAMILY_REUNION = "family_reunion", "Family Reunion"
        MULTI_FAMILY_TRIP = "multi_family_trip", "Multi-Family Trip"
        WEDDING = "wedding", "Wedding"
        FRIEND_GROUP = "friend_group", "Friend Group"
        CORPORATE_RETREAT = "corporate_retreat", "Corporate Retreat"
        RETREAT = "retreat", "Retreat"
        OTHER = "other", "Other"

    name = models.CharField(max_length=150)

    group_type = models.CharField(
        max_length=40,
        choices=GroupType.choices,
        default=GroupType.MULTI_FAMILY_TRIP,
    )

    primary_contact = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_travel_groups",
    )

    notes = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["group_type"]),
        ]

    def __str__(self):
        return self.name


class TravelGroupMember(models.Model):
    class Role(models.TextChoices):
        PRIMARY_ORGANIZER = "primary_organizer", "Primary Organizer"
        FAMILY_UNIT = "family_unit", "Family Unit"
        GUEST = "guest", "Guest"
        BILLING_CONTACT = "billing_contact", "Billing Contact"
        EVENT_CONTACT = "event_contact", "Event Contact"
        OTHER = "other", "Other"

    travel_group = models.ForeignKey(
        TravelGroup,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="travel_group_memberships",
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="travel_group_memberships",
    )

    role = models.CharField(
        max_length=40,
        choices=Role.choices,
        default=Role.GUEST,
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["travel_group__name", "role", "created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(household__isnull=False, client__isnull=True)
                    | models.Q(household__isnull=True, client__isnull=False)
                ),
                name="travel_group_member_household_or_client_not_both",
            ),
        ]

    def __str__(self):
        member = self.household or self.client
        return f"{member} - {self.travel_group}"

    def clean(self):
        if self.household and self.client:
            raise ValidationError("A travel group member cannot be both a household and a client.")

        if not self.household and not self.client:
            raise ValidationError("A travel group member must be either a household or a client.")


class ClientNote(models.Model):
    class NoteType(models.TextChoices):
        GENERAL = "general", "General"
        PREFERENCE = "preference", "Preference"
        MEDICAL = "medical", "Medical"
        DIETARY = "dietary", "Dietary"
        RIDING = "riding", "Riding"
        RESERVATION = "reservation", "Reservation"
        FOLLOW_UP = "follow_up", "Follow-Up"
        WARNING = "warning", "Warning"

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="notes",
    )

    title = models.CharField(max_length=150)
    note = models.TextField()

    note_type = models.CharField(
        max_length=30,
        choices=NoteType.choices,
        default=NoteType.GENERAL,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="client_notes",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["note_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.client} - {self.title}"
