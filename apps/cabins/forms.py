from django import forms

from .models import Cabin


class CabinForm(forms.ModelForm):
    class Meta:
        model = Cabin
        fields = [
            "name",
            "cabin_number",
            "capacity",
            "bed_configuration",
            "description",
            "status",
            "housekeeping_status",
            "notes",
            "is_active",
            "sort_order",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }