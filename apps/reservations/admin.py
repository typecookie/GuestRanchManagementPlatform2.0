from django.contrib import admin

from .models import OperatingSeason, Reservation, ReservationCabin, ReservationFlight, ReservationGuest


@admin.register(OperatingSeason)
class OperatingSeasonAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "start_date",
        "end_date",
        "duration_days",
        "duration_weeks",
        "is_active",
        "updated_at",
    ]
    list_filter = [
        "is_active",
        "start_date",
        "end_date",
    ]
    search_fields = [
        "name",
        "notes",
    ]
    date_hierarchy = "start_date"
    ordering = [
        "start_date",
        "name",
    ]


class ReservationFlightInline(admin.TabularInline):
    model = ReservationFlight
    extra = 1
    fields = [
        "flight_type",
        "airport",
        "flight_number",
        "flight_date",
        "flight_time",
        "notes",
    ]


class ReservationCabinInline(admin.TabularInline):
    model = ReservationCabin
    extra = 1
    autocomplete_fields = ["cabin"]
    fields = [
        "cabin",
        "arrival_date",
        "departure_date",
        "notes",
    ]

class ReservationGuestInline(admin.TabularInline):
    model = ReservationGuest
    extra = 1
    autocomplete_fields = ["client", "cabin"]
    fields = [
        "client",
        "cabin",
        "age_at_stay",
        "riding_experience",
        "is_riding",
        "allergies",
        "food_requests",
        "medical_notes",
    ]
    
@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = [
        "reservation_name",
        "reservation_type",
        "status",
        "arrival_date",
        "departure_date",
        "primary_contact",
        "household",
        "travel_group",
        "display_guest_count",
    ]
    list_filter = [
        "reservation_type",
        "status",
        "is_driving",
        "is_flying",
        "arrival_date",
        "departure_date",
    ]
    search_fields = [
        "reservation_name",
        "primary_contact__first_name",
        "primary_contact__middle_name",
        "primary_contact__last_name",
        "household__name",
        "travel_group__name",
        "driving_notes",
        "flying_notes",
        "notes",
        "internal_notes",
    ]
    autocomplete_fields = [
        "primary_contact",
        "household",
        "travel_group",
    ]
    date_hierarchy = "arrival_date"
    ordering = [
        "arrival_date",
        "reservation_name",
    ]
    inlines = [
        ReservationFlightInline,
        ReservationCabinInline,
        ReservationGuestInline,
    ]


@admin.register(ReservationFlight)
class ReservationFlightAdmin(admin.ModelAdmin):
    list_display = [
        "reservation",
        "airport",
        "flight_type",
        "flight_number",
        "flight_date",
        "flight_time",
    ]
    list_filter = [
        "airport",
        "flight_type",
        "flight_date",
    ]
    search_fields = [
        "reservation__reservation_name",
        "airport",
        "flight_number",
        "notes",
    ]
    autocomplete_fields = [
        "reservation",
    ]
    ordering = [
        "airport",
        "flight_type",
        "flight_date",
        "flight_time",
    ]


@admin.register(ReservationCabin)
class ReservationCabinAdmin(admin.ModelAdmin):
    list_display = [
        "reservation",
        "cabin",
        "arrival_date",
        "departure_date",
    ]
    list_filter = [
        "arrival_date",
        "departure_date",
        "cabin",
        "reservation__status",
    ]
    search_fields = [
        "reservation__reservation_name",
        "cabin__name",
        "cabin__cabin_number",
        "notes",
    ]
    autocomplete_fields = [
        "reservation",
        "cabin",
    ]
    date_hierarchy = "arrival_date"
    ordering = [
        "arrival_date",
        "cabin__capacity",
        "cabin__sort_order",
        "cabin__name",
    ]

@admin.register(ReservationGuest)
class ReservationGuestAdmin(admin.ModelAdmin):
    list_display = [
        "reservation",
        "client",
        "cabin",
        "age_at_stay",
        "display_height",
        "display_weight",
        "riding_experience",
        "is_riding",
    ]
    list_filter = [
        "cabin",
        "riding_experience",
        "is_riding",
    ]
    search_fields = [
        "reservation__reservation_name",
        "client__first_name",
        "client__middle_name",
        "client__last_name",
        "cabin__name",
        "cabin__cabin_number",
        "allergies",
        "food_requests",
        "medical_notes",
        "notes",
    ]
    autocomplete_fields = [
        "reservation",
        "client",
        "cabin",
    ]

    @admin.display(description="Height")
    def display_height(self, obj):
        return obj.height

    @admin.display(description="Weight")
    def display_weight(self, obj):
        return obj.weight
