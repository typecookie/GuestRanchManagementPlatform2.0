from django.db import models


class Contractor(models.Model):
    class Category(models.TextChoices):
        DISTRIBUTOR = "distributor", "Distributor"
        CONTRACTOR = "contractor", "Contractor"
        SUPPLIER = "supplier", "Supplier / Vendor"
        SERVICE = "service", "Service Provider"
        OTHER = "other", "Other"

    name = models.CharField(max_length=255, help_text="Business or contractor name")
    contact_name = models.CharField(max_length=255, blank=True, verbose_name="Contact Person", help_text="Primary sales rep or contact person")
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.DISTRIBUTOR,
        verbose_name="Type / Category"
    )
    phone = models.CharField(max_length=50, blank=True, help_text="Primary phone number")
    email = models.EmailField(blank=True, help_text="Contact email address")
    
    # Location / Address fields
    address_line_1 = models.CharField(max_length=255, blank=True, verbose_name="Address Line 1")
    address_line_2 = models.CharField(max_length=255, blank=True, verbose_name="Address Line 2")
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True, verbose_name="State / Province")
    postal_code = models.CharField(max_length=30, blank=True, verbose_name="Postal Code")
    
    website = models.URLField(blank=True, help_text="e.g. https://example.com")
    notes = models.TextField(blank=True, help_text="Additional information, delivery terms, account numbers, etc.")
    is_active = models.BooleanField(default=True, verbose_name="Active")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Distributor / Contractor"
        verbose_name_plural = "Distributors & Contractors"

    def __str__(self):
        return self.name

    @property
    def full_address(self):
        parts = []
        if self.address_line_1:
            parts.append(self.address_line_1)
        if self.address_line_2:
            parts.append(self.address_line_2)
        
        city_state_zip = []
        if self.city:
            city_state_zip.append(self.city)
        if self.state:
            city_state_zip.append(self.state)
        
        loc_str = ", ".join(city_state_zip)
        if self.postal_code:
            loc_str = f"{loc_str} {self.postal_code}".strip()
        
        if loc_str:
            parts.append(loc_str)
            
        return ", ".join(parts) if parts else ""
