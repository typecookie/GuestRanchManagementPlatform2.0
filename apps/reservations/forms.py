from datetime import time

from django import forms

from .models import Reservation, ReservationCabin, ReservationGuest


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [
            "reservation_name",
            "reservation_type",
            "status",
            "primary_contact",
            "household",
            "travel_group",
            "arrival_date",
            "departure_date",
            "check_in_time",
            "check_out_time",
            "adult_count",
            "child_count",
            "guest_count",
            "notes",
            "internal_notes",
        ]
        widgets = {
            "primary_contact": forms.Select(
                attrs={
                    "class": "js-searchable-select",
                    "data-placeholder": "Search clients...",
                }
            ),
            "household": forms.Select(
                attrs={
                    "class": "js-searchable-select",
                    "data-placeholder": "Search households...",
                }
            ),
            "travel_group": forms.Select(
                attrs={
                    "class": "js-searchable-select",
                    "data-placeholder": "Search travel groups...",
                }
            ),
            "arrival_date": forms.DateInput(attrs={"type": "date"}),
            "departure_date": forms.DateInput(attrs={"type": "date"}),
            "check_in_time": forms.TimeInput(attrs={"type": "time"}),
            "check_out_time": forms.TimeInput(attrs={"type": "time"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
            "internal_notes": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        arrival_date = cleaned_data.get("arrival_date")
        departure_date = cleaned_data.get("departure_date")

        if arrival_date and departure_date and departure_date <= arrival_date:
            raise forms.ValidationError("Departure date must be after arrival date.")

        return cleaned_data


class ReservationCabinForm(forms.ModelForm):
    class Meta:
        model = ReservationCabin
        fields = [
            "cabin",
            "arrival_date",
            "departure_date",
            "notes",
        ]
        widgets = {
            "cabin": forms.Select(
                attrs={
                    "class": "js-searchable-select",
                    "data-placeholder": "Search cabins...",
                }
            ),
            "arrival_date": forms.DateInput(attrs={"type": "date"}),
            "departure_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        arrival_date = cleaned_data.get("arrival_date")
        departure_date = cleaned_data.get("departure_date")

        if arrival_date and departure_date and departure_date <= arrival_date:
            raise forms.ValidationError("Cabin departure date must be after cabin arrival date.")

        return cleaned_data


class ReservationGuestForm(forms.ModelForm):
    class Meta:
        model = ReservationGuest
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
            "notes",
        ]
        widgets = {
            "client": forms.Select(
                attrs={
                    "class": "js-searchable-select",
                    "data-placeholder": "Search clients...",
                }
            ),
            "cabin": forms.Select(
                attrs={
                    "class": "js-searchable-select",
                    "data-placeholder": "Search cabins...",
                }
            ),
            "allergies": forms.Textarea(attrs={"rows": 3}),
            "food_requests": forms.Textarea(attrs={"rows": 3}),
            "medical_notes": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }