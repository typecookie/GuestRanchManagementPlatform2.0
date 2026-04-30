from django.contrib import admin

from .models import Reservation, ReservationCabin, ReservationGuest


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
        "height",
        "weight",
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
        ReservationCabinInline,
        ReservationGuestInline,
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
        "height",
        "weight",
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
