from django import forms
from django.urls import reverse_lazy

from .models import (
    Client,
    ClientNote,
    Household,
    HouseholdMember,
    TravelGroup,
    TravelGroupMember,
    calculate_age_at_date,
)


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            "first_name",
            "middle_name",
            "last_name",
            "preferred_name",
            "email",
            "phone",
            "alternate_phone",
            "date_of_birth",
            "age",
            "sex",
            "client_type",
            "is_rider",
            "riding_level",
            "height",
            "weight",
            "saddle_preference",
            "rider_notes",
            "years_return",
            "dietary_notes",
            "medical_notes",
            "general_notes",
            "is_active",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date", "class": "form-input js-client-dob"}),
            "age": forms.NumberInput(attrs={"class": "form-control js-client-age", "min": 0, "max": 130, "placeholder": "e.g. 35"}),
            "sex": forms.Select(attrs={"class": "form-select"}),
            "height": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 5'8\" or 68 in"}),
            "weight": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 150 lbs"}),
            "saddle_preference": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 15\" Western, Youth, etc."}),
            "rider_notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Special horse matching notes, saddle size, comfort requirements, or riding goals."}),
            "years_return": forms.NumberInput(attrs={"class": "form-control", "min": 1, "placeholder": "e.g. 5"}),
            "dietary_notes": forms.Textarea(attrs={"rows": 4}),
            "medical_notes": forms.Textarea(attrs={"rows": 4}),
            "general_notes": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        dob = cleaned_data.get("date_of_birth")
        age = cleaned_data.get("age")
        if dob and age is None:
            cleaned_data["age"] = calculate_age_at_date(dob)
        return cleaned_data


class HouseholdForm(forms.ModelForm):
    class Meta:
        model = Household
        fields = [
            "name",
            "primary_contact",
            "billing_contact",
            "years_return",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "postal_code",
            "country",
            "notes",
            "is_active",
        ]
        widgets = {
            "primary_contact": forms.Select(
                attrs={
                    "class": "js-searchable-select",
                    "data-placeholder": "Search clients...",
                    "data-create-url": reverse_lazy("clients:client_create"),
                    "data-quick-add-url": reverse_lazy("clients:quick_add_client"),
                }
            ),
            "billing_contact": forms.Select(
                attrs={
                    "class": "js-searchable-select",
                    "data-placeholder": "Search clients...",
                    "data-create-url": reverse_lazy("clients:client_create"),
                    "data-quick-add-url": reverse_lazy("clients:quick_add_client"),
                }
            ),
            "years_return": forms.NumberInput(attrs={"class": "form-control", "min": 1, "placeholder": "e.g. 5"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }


class TravelGroupForm(forms.ModelForm):
    class Meta:
        model = TravelGroup
        fields = [
            "name",
            "group_type",
            "primary_contact",
            "years_return",
            "notes",
            "is_active",
        ]
        widgets = {
            "primary_contact": forms.Select(
                attrs={
                    "class": "js-searchable-select",
                    "data-placeholder": "Search clients...",
                    "data-create-url": reverse_lazy("clients:client_create"),
                    "data-quick-add-url": reverse_lazy("clients:quick_add_client"),
                }
            ),
            "years_return": forms.NumberInput(attrs={"class": "form-control", "min": 1, "placeholder": "e.g. 5"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }


class ClientNoteForm(forms.ModelForm):
    class Meta:
        model = ClientNote
        fields = [
            "title",
            "note_type",
            "note",
        ]
        widgets = {
            "note": forms.Textarea(attrs={"rows": 5}),
        }


class HouseholdMemberForm(forms.ModelForm):
    class Meta:
        model = HouseholdMember
        fields = [
            "client",
            "relationship",
            "is_primary_contact",
            "is_billing_contact",
            "notes",
        ]
        widgets = {
            "client": forms.Select(
                attrs={
                    "class": "js-searchable-select",
                    "data-placeholder": "Search clients...",
                    "data-quick-add-url": reverse_lazy("clients:quick_add_client"),
                }
            ),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class TravelGroupMemberForm(forms.ModelForm):
    class Meta:
        model = TravelGroupMember
        fields = [
            "household",
            "client",
            "role",
            "notes",
        ]
        widgets = {
            "household": forms.Select(
                attrs={
                    "class": "js-searchable-select",
                    "data-placeholder": "Search households...",
                    "data-quick-add-url": reverse_lazy("clients:quick_add_household"),
                }
            ),
            "client": forms.Select(
                attrs={
                    "class": "js-searchable-select",
                    "data-placeholder": "Search clients...",
                    "data-quick-add-url": reverse_lazy("clients:quick_add_client"),
                }
            ),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        household = cleaned_data.get("household")
        client = cleaned_data.get("client")

        if household and client:
            raise forms.ValidationError("Choose either a household or an individual client, not both.")

        if not household and not client:
            raise forms.ValidationError("Choose either a household or an individual client.")

        return cleaned_data