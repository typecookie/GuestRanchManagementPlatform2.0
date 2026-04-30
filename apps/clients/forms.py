from django import forms

from .models import (
    Client,
    ClientNote,
    Household,
    HouseholdMember,
    TravelGroup,
    TravelGroupMember,
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
            "client_type",
            "riding_level",
            "dietary_notes",
            "medical_notes",
            "general_notes",
            "is_active",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "dietary_notes": forms.Textarea(attrs={"rows": 4}),
            "medical_notes": forms.Textarea(attrs={"rows": 4}),
            "general_notes": forms.Textarea(attrs={"rows": 4}),
        }


class HouseholdForm(forms.ModelForm):
    class Meta:
        model = Household
        fields = [
            "name",
            "primary_contact",
            "billing_contact",
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
            "notes": forms.Textarea(attrs={"rows": 4}),
        }


class TravelGroupForm(forms.ModelForm):
    class Meta:
        model = TravelGroup
        fields = [
            "name",
            "group_type",
            "primary_contact",
            "notes",
            "is_active",
        ]
        widgets = {
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
            "client": forms.Select(attrs={"class": "js-searchable-select"}),
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
                }
            ),
            "client": forms.Select(
                attrs={
                    "class": "js-searchable-select",
                    "data-placeholder": "Search clients...",
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