from django import forms
from django.urls import reverse_lazy
from .models import BarInventoryItem, BarItemTag
from apps.contractors.models import Contractor


class BarItemTagForm(forms.ModelForm):
    class Meta:
        model = BarItemTag
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Whisky, Rum, Dark Rum'}),
        }


class BarInventoryItemForm(forms.ModelForm):
    custom_tags = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_custom_tags'}),
        help_text="Comma-separated tag names to create or associate"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Show all active distributors / contractors
        self.fields['distributor'].queryset = Contractor.objects.filter(is_active=True).order_by('name')
        self.fields['distributor'].required = False
        self.fields['tags'].queryset = BarItemTag.objects.all().order_by('name')
        self.fields['tags'].required = False
        self.fields['beverage_class'].required = False
        self.fields['sale_price'].required = False

    class Meta:
        model = BarInventoryItem
        fields = [
            'stock_number', 'description', 'category', 'pricing_method', 'beverage_class',
            'tags', 'on_hand', 'minimum_on_hand',
            'single_price', 'case_price', 'sale_price', 'singles_per_case',
            'distributor', 'location', 'unit_type', 'notes', 'is_active'
        ]
        widgets = {
            'stock_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. STK-101 or B-042'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Maker\'s Mark Bourbon 750ml'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'pricing_method': forms.Select(attrs={'class': 'form-select', 'id': 'id_pricing_method'}),
            'beverage_class': forms.Select(attrs={'class': 'form-select', 'id': 'id_beverage_class'}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-select js-tags-select', 'style': 'display: none;'}),
            'on_hand': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'minimum_on_hand': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'single_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'case_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'singles_per_case': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': '12'}),
            'distributor': forms.Select(attrs={
                'class': 'form-select js-searchable-select',
                'data-placeholder': 'Search or select distributor...',
                'data-quick-add-url': reverse_lazy('contractors:quick_add_contractor'),
            }),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Main Bar, Cooler, Back Stock'}),
            'unit_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Bottle, Can, Keg, Case'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Vintage notes, supplier codes, ordering notes...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        pricing_method = cleaned_data.get('pricing_method')
        beverage_class = cleaned_data.get('beverage_class')

        if pricing_method == BarInventoryItem.PricingMethod.BY_CLASS:
            if not beverage_class:
                self.add_error('beverage_class', 'Please select a class (Call, Well, Top Shelf, Domestic, or Import) when selling by class.')
        elif pricing_method == BarInventoryItem.PricingMethod.BY_PRICE:
            cleaned_data['beverage_class'] = None

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=commit)
        custom_tags_str = self.cleaned_data.get('custom_tags', '')
        if custom_tags_str:
            tag_names = [t.strip() for t in custom_tags_str.split(',') if t.strip()]
            new_tag_objs = []
            for name in tag_names:
                tag_obj, _ = BarItemTag.objects.get_or_create(name=name)
                new_tag_objs.append(tag_obj)
            
            if commit:
                instance.tags.add(*new_tag_objs)
            else:
                old_save_m2m = getattr(self, 'save_m2m', None)
                def new_save_m2m():
                    if old_save_m2m:
                        old_save_m2m()
                    instance.tags.add(*new_tag_objs)
                self.save_m2m = new_save_m2m

        return instance
