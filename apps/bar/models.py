import math
from decimal import Decimal
from django.db import models


class BarItemTag(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Tag / Type Name",
        help_text="e.g. Whisky, Rum, Dark Rum, Bourbon, Tequila, Vodka, IPA"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Bar Item Tag"
        verbose_name_plural = "Bar Item Tags"

    def __str__(self):
        return self.name


class BarInventoryItem(models.Model):
    class Category(models.TextChoices):
        LIQUOR = "liquor", "Spirits & Liquor"
        BEER = "beer", "Beer & Cider"
        WINE = "wine", "Wine & Champagne"
        MIXERS = "mixers", "Mixers & Non-Alcoholic"
        SUPPLIES = "supplies", "Bar Supplies & Garnishes"
        OTHER = "other", "Other"

    class PricingMethod(models.TextChoices):
        BY_PRICE = "by_price", "By Price"
        BY_CLASS = "by_class", "By Class"

    class BeverageClass(models.TextChoices):
        CALL = "call", "Call"
        WELL = "well", "Well"
        TOP = "top", "Top Shelf"
        DOMESTIC = "domestic", "Domestic"
        IMPORT = "import", "Import"

    # Specific fields requested:
    # 1. Stock number
    # 2. Description
    # 3. On hand
    # 4. Minimums on hand
    # 5. Single price
    # 6. Case price
    # 7. Sale price
    # 8. Singles per case
    # 9. Distributor field
    # 10. Total value (calculated: on hand * single price)
    # 11. Pricing method (By Price vs By Class)
    # 12. Beverage class (Call, Well, Top, Domestic, Import)

    stock_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Stock Number",
        help_text="Unique stock number or SKU (e.g. STK-101, B-042)"
    )
    description = models.CharField(
        max_length=255,
        verbose_name="Description",
        help_text="Item description / name (e.g. Maker's Mark Bourbon 750ml, Coors Banquet 12oz)"
    )
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.LIQUOR,
        verbose_name="Category"
    )
    pricing_method = models.CharField(
        max_length=20,
        choices=PricingMethod.choices,
        default=PricingMethod.BY_CLASS,
        verbose_name="Pricing Method",
        help_text="How alcohol is sold: by price or by class"
    )
    beverage_class = models.CharField(
        max_length=20,
        choices=BeverageClass.choices,
        blank=True,
        null=True,
        verbose_name="Beverage Class / Tier",
        help_text="Class tier if sold by class: Call, Well, Top, Domestic, or Import"
    )
    tags = models.ManyToManyField(
        'BarItemTag',
        blank=True,
        related_name='bar_items',
        verbose_name="Types / Tags",
        help_text="Tag-style types (e.g. Whisky, Rum, Dark Rum, Bourbon, Tequila, Vodka, IPA)"
    )
    on_hand = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="On Hand",
        help_text="Current number of units / singles in stock"
    )
    minimum_on_hand = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Minimum On Hand",
        help_text="Minimum threshold quantity before reordering"
    )
    single_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Single Price",
        help_text="Cost price paid per single bottle/unit"
    )
    case_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Case Price",
        help_text="Cost price paid per case pack"
    )
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Sale Price",
        help_text="Standard menu / retail price (we don't track actual charge for well/call/top)"
    )
    singles_per_case = models.PositiveIntegerField(
        default=1,
        verbose_name="Singles per Case",
        help_text="Number of single bottles / cans / units in one case pack"
    )
    distributor = models.ForeignKey(
        'contractors.Contractor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bar_items',
        verbose_name="Distributor",
        help_text="Beverage distributor or supplier"
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        default="Main Bar",
        verbose_name="Storage Location",
        help_text="e.g. Main Bar, Back Storage, Cooler, Wine Cellar"
    )
    unit_type = models.CharField(
        max_length=50,
        blank=True,
        default="Bottle",
        verbose_name="Unit Type",
        help_text="e.g. Bottle, Can, Keg, Pack, Box"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="Special ordering instructions, vintage notes, seasonal item..."
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'description', 'stock_number']
        verbose_name = "Bar Inventory Item"
        verbose_name_plural = "Bar Inventory Items"

    def __str__(self):
        return f"[{self.stock_number}] {self.description}"

    @property
    def total_value(self):
        """
        Total Value = number on hand * single price
        """
        units = self.on_hand if self.on_hand is not None else Decimal('0.00')
        price = self.single_price if self.single_price is not None else Decimal('0.00')
        return (units * price).quantize(Decimal('0.01'))

    @property
    def is_low_stock(self):
        """
        True if current on hand is at or below the minimum threshold.
        """
        units = self.on_hand if self.on_hand is not None else Decimal('0.00')
        min_units = self.minimum_on_hand if self.minimum_on_hand is not None else Decimal('0.00')
        return units <= min_units

    @property
    def reorder_needed(self):
        """
        Number of singles required to get back up to minimum on hand.
        """
        units = self.on_hand if self.on_hand is not None else Decimal('0.00')
        min_units = self.minimum_on_hand if self.minimum_on_hand is not None else Decimal('0.00')
        if units < min_units:
            return min_units - units
        return Decimal('0.00')

    @property
    def suggested_cases_to_order(self):
        """
        Calculates suggested whole cases to order based on reorder_needed and singles_per_case.
        """
        needed = self.reorder_needed
        if needed <= 0 or not self.singles_per_case:
            return 0
        return math.ceil(float(needed) / float(self.singles_per_case))

    @property
    def estimated_reorder_cost(self):
        """
        Estimated cost to reorder needed cases or units.
        """
        cases = self.suggested_cases_to_order
        if cases > 0 and self.case_price and self.case_price > 0:
            return (Decimal(cases) * self.case_price).quantize(Decimal('0.01'))
        needed = self.reorder_needed
        if needed > 0 and self.single_price:
            return (needed * self.single_price).quantize(Decimal('0.01'))
        return Decimal('0.00')

    @property
    def is_by_class(self):
        return self.pricing_method == self.PricingMethod.BY_CLASS

    @property
    def is_by_price(self):
        return self.pricing_method == self.PricingMethod.BY_PRICE

    @property
    def is_top_shelf(self):
        return self.beverage_class == self.BeverageClass.TOP

    @property
    def pricing_display(self):
        """
        Formatted display of pricing tier or sale price.
        """
        if self.is_by_class:
            if self.is_top_shelf:
                if self.sale_price and self.sale_price > 0:
                    return f"Top Shelf (${self.sale_price:.2f})"
                return "Top Shelf"
            if self.beverage_class:
                return self.get_beverage_class_display()
            return "By Class"
        else:
            if self.sale_price and self.sale_price > 0:
                return f"${self.sale_price:.2f}"
            return "By Price"
