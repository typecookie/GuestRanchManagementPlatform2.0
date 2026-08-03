from datetime import time

from django import forms
from django.urls import reverse_lazy
from django.db.models.functions import Length

from .models import Reservation, ReservationCabin, ReservationGuest
from apps.horses.models import Horse, Saddle


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
            "deposit_request_sent",
            "deposit_received",
            "notes",
            "internal_notes",
        ]
        widgets = {
            "primary_contact": forms.Select(
                attrs={
                    "class": "js-searchable-select",
                    "data-placeholder": "Search clients...",
                    "data-create-url": reverse_lazy("clients:client_create"),
                    "data-quick-add-url": reverse_lazy("clients:quick_add_client"),
                    "data-context-fields": "travel_group,household",
                }
            ),
            "household": forms.Select(
                attrs={
                    "class": "js-searchable-select",
                    "data-placeholder": "Search households...",
                    "data-create-url": reverse_lazy("clients:household_create"),
                    "data-quick-add-url": reverse_lazy("clients:quick_add_household"),
                    "data-context-fields": "travel_group",
                }
            ),
            "travel_group": forms.Select(
                attrs={
                    "class": "js-searchable-select",
                    "data-placeholder": "Search travel groups...",
                    "data-create-url": reverse_lazy("clients:travel_group_create"),
                    "data-quick-add-url": reverse_lazy("clients:quick_add_travel_group"),
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
    def __init__(self, *args, **kwargs):
        reservation = kwargs.pop('reservation', None)
        super().__init__(*args, **kwargs)
        if reservation:
            if reservation.travel_group_id:
                self.fields['client'].widget.attrs['data-context-value-travel-group'] = reservation.travel_group_id
            if reservation.household_id:
                self.fields['client'].widget.attrs['data-context-value-household'] = reservation.household_id

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
            "signed_release",
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
                    "data-quick-add-url": reverse_lazy("clients:quick_add_client"),
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


class HorseAssignmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active horses and in-service saddles, 
        # but also include the currently assigned ones if they are not active/in-service
        
        active_horses = Horse.objects.filter(status=Horse.Status.ACTIVE)
        if self.instance and self.instance.horse_id:
            active_horses = active_horses | Horse.objects.filter(pk=self.instance.horse_id)
        self.fields['horse'].queryset = active_horses.distinct()
        
        in_service_saddles = Saddle.objects.filter(status=Saddle.Status.IN_SERVICE)
        if self.instance and self.instance.saddle_id:
            in_service_saddles = in_service_saddles | Saddle.objects.filter(pk=self.instance.saddle_id)
        
        self.fields['saddle'].queryset = in_service_saddles.annotate(
            rack_len=Length('rack_number')
        ).order_by('status', 'rack_len', 'rack_number', 'saddle_number').distinct()

    class Meta:
        model = ReservationGuest
        fields = ["horse", "saddle"]
        widgets = {
            "horse": forms.Select(
                attrs={
                    "class": "js-searchable-select horse-assignment-select",
                    "data-placeholder": "Assign horse...",
                }
            ),
            "saddle": forms.Select(
                attrs={
                    "class": "js-searchable-select saddle-assignment-select",
                    "data-placeholder": "Assign saddle...",
                }
            ),
        }