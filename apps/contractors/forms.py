from django import forms
from .models import Contractor


class ContractorForm(forms.ModelForm):
    class Meta:
        model = Contractor
        fields = [
            'name', 'contact_name', 'category', 'phone', 'email',
            'address_line_1', 'address_line_2', 'city', 'state', 'postal_code',
            'website', 'notes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Western Beverage Distributing'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. John Miller (Sales Rep)'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. (307) 555-0199'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'e.g. orders@westernbev.com'}),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street address'}),
            'address_line_2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Suite, Unit, Bldg'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'WY'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal Code'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'placeholder': 'Delivery schedule, account terms, notes...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
