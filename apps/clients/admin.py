from django.contrib import admin

from .models import (
    Client,
    ClientNote,
    Household,
    HouseholdMember,
    TravelGroup,
    TravelGroupMember,
)


class HouseholdMemberInline(admin.TabularInline):
    model = HouseholdMember
    extra = 1
    autocomplete_fields = ["client"]


class TravelGroupMemberInline(admin.TabularInline):
    model = TravelGroupMember
    extra = 1
    autocomplete_fields = ["household", "client"]


class ClientNoteInline(admin.TabularInline):
    model = ClientNote
    extra = 0
    fields = ["title", "note_type", "note", "created_by", "created_at"]
    readonly_fields = ["created_at"]
    autocomplete_fields = ["created_by"]


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = [
        "full_name",
        "preferred_name",
        "middle_name",
        "client_type",
        "riding_level",
        "email",
        "phone",
        "is_active",
    ]
    list_filter = [
        "client_type",
        "riding_level",
        "is_active",
    ]
    search_fields = [
        "first_name",
        "middle_name",
        "last_name",
        "preferred_name",
        "email",
        "phone",
        "alternate_phone",
    ]
    ordering = ["last_name", "first_name"]
    inlines = [ClientNoteInline]


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "primary_contact",
        "billing_contact",
        "city",
        "state",
        "is_active",
    ]
    list_filter = [
        "is_active",
        "state",
        "country",
    ]
    search_fields = [
        "name",
        "primary_contact__first_name",
        "primary_contact__last_name",
        "billing_contact__first_name",
        "billing_contact__last_name",
        "city",
        "state",
    ]
    autocomplete_fields = [
        "primary_contact",
        "billing_contact",
    ]
    inlines = [HouseholdMemberInline]


@admin.register(HouseholdMember)
class HouseholdMemberAdmin(admin.ModelAdmin):
    list_display = [
        "household",
        "client",
        "relationship",
        "is_primary_contact",
        "is_billing_contact",
    ]
    list_filter = [
        "relationship",
        "is_primary_contact",
        "is_billing_contact",
    ]
    search_fields = [
        "household__name",
        "client__first_name",
        "client__last_name",
    ]
    autocomplete_fields = [
        "household",
        "client",
    ]


@admin.register(TravelGroup)
class TravelGroupAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "group_type",
        "primary_contact",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "group_type",
        "is_active",
    ]
    search_fields = [
        "name",
        "primary_contact__first_name",
        "primary_contact__last_name",
    ]
    autocomplete_fields = [
        "primary_contact",
    ]
    inlines = [TravelGroupMemberInline]


@admin.register(TravelGroupMember)
class TravelGroupMemberAdmin(admin.ModelAdmin):
    list_display = [
        "travel_group",
        "household",
        "client",
        "role",
    ]
    list_filter = [
        "role",
    ]
    search_fields = [
        "travel_group__name",
        "household__name",
        "client__first_name",
        "client__last_name",
    ]
    autocomplete_fields = [
        "travel_group",
        "household",
        "client",
    ]


@admin.register(ClientNote)
class ClientNoteAdmin(admin.ModelAdmin):
    list_display = [
        "client",
        "title",
        "note_type",
        "created_by",
        "created_at",
    ]
    list_filter = [
        "note_type",
        "created_at",
    ]
    search_fields = [
        "client__first_name",
        "client__last_name",
        "title",
        "note",
    ]
    autocomplete_fields = [
        "client",
        "created_by",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
    ]
