from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from apps.bar.models import BarInventoryItem, BarItemTag
from apps.contractors.models import Contractor


class BarInventoryAndReportsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="baradmin",
            password="password123",
            email="bar@guestranch.com"
        )
        self.client.login(username="baradmin", password="password123")

        self.tag_whisky = BarItemTag.objects.create(name="Whisky")
        self.tag_bourbon = BarItemTag.objects.create(name="Bourbon")
        self.tag_gin = BarItemTag.objects.create(name="Gin")
        self.tag_rum = BarItemTag.objects.create(name="Rum")
        self.tag_dark_rum = BarItemTag.objects.create(name="Dark Rum")
        self.tag_ipa = BarItemTag.objects.create(name="IPA")

        self.distributor1 = Contractor.objects.create(
            name="Wyoming Wine & Spirits Distributing",
            contact_name="Alice Adams",
            category=Contractor.Category.DISTRIBUTOR,
            phone="307-555-4400",
            email="alice@wyowine.com",
            address_line_1="500 Distro Lane",
            city="Casper",
            state="WY",
            postal_code="82601"
        )

        self.distributor2 = Contractor.objects.create(
            name="Snake River Beer Co",
            contact_name="Sam Craft",
            category=Contractor.Category.DISTRIBUTOR,
            phone="307-555-7711",
            email="sam@snakeriverbeer.com",
            address_line_1="265 Broadway",
            city="Jackson",
            state="WY",
            postal_code="83001"
        )

        # Item 1: Well stocked Bourbon with tags (Top shelf with custom sale price)
        self.item_bourbon = BarInventoryItem.objects.create(
            stock_number="LIQ-1001",
            description="Maker's Mark Kentucky Bourbon 750ml",
            category=BarInventoryItem.Category.LIQUOR,
            pricing_method=BarInventoryItem.PricingMethod.BY_CLASS,
            beverage_class=BarInventoryItem.BeverageClass.TOP,
            on_hand=Decimal('18.00'),
            minimum_on_hand=Decimal('6.00'),
            single_price=Decimal('28.50'),
            case_price=Decimal('310.00'),
            sale_price=Decimal('14.50'),
            singles_per_case=12,
            distributor=self.distributor1,
            location="Main Bar",
            unit_type="Bottle"
        )
        self.item_bourbon.tags.add(self.tag_whisky, self.tag_bourbon)

        # Item 2: Low stock Gin (Call class)
        self.item_gin = BarInventoryItem.objects.create(
            stock_number="LIQ-1002",
            description="Hendrick's Gin 750ml",
            category=BarInventoryItem.Category.LIQUOR,
            pricing_method=BarInventoryItem.PricingMethod.BY_CLASS,
            beverage_class=BarInventoryItem.BeverageClass.CALL,
            on_hand=Decimal('2.00'),
            minimum_on_hand=Decimal('8.00'),
            single_price=Decimal('32.00'),
            case_price=Decimal('350.00'),
            sale_price=Decimal('0.00'),
            singles_per_case=12,
            distributor=self.distributor1,
            location="Main Bar",
            unit_type="Bottle"
        )
        self.item_gin.tags.add(self.tag_gin)

        # Item 3: Low stock Beer (Domestic class)
        self.item_beer = BarInventoryItem.objects.create(
            stock_number="BER-2001",
            description="Snake River Pako's IPA 12oz Cans",
            category=BarInventoryItem.Category.BEER,
            pricing_method=BarInventoryItem.PricingMethod.BY_CLASS,
            beverage_class=BarInventoryItem.BeverageClass.DOMESTIC,
            on_hand=Decimal('10.00'),
            minimum_on_hand=Decimal('48.00'),
            single_price=Decimal('1.85'),
            case_price=Decimal('42.00'),
            sale_price=Decimal('0.00'),
            singles_per_case=24,
            distributor=self.distributor2,
            location="Cooler",
            unit_type="Can"
        )
        self.item_beer.tags.add(self.tag_ipa)

        # Item 4: Rum with Dark Rum tag (Well class)
        self.item_rum = BarInventoryItem.objects.create(
            stock_number="LIQ-1003",
            description="Kraken Black Spiced Rum 750ml",
            category=BarInventoryItem.Category.LIQUOR,
            pricing_method=BarInventoryItem.PricingMethod.BY_CLASS,
            beverage_class=BarInventoryItem.BeverageClass.WELL,
            on_hand=Decimal('12.00'),
            minimum_on_hand=Decimal('4.00'),
            single_price=Decimal('22.00'),
            case_price=Decimal('240.00'),
            sale_price=Decimal('0.00'),
            singles_per_case=12,
            distributor=self.distributor1,
            location="Main Bar",
            unit_type="Bottle"
        )
        self.item_rum.tags.add(self.tag_rum, self.tag_dark_rum)

    def test_bar_item_calculations(self):
        # Bourbon: 18 * 28.50 = 513.00
        self.assertEqual(self.item_bourbon.total_value, Decimal('513.00'))
        self.assertFalse(self.item_bourbon.is_low_stock)
        self.assertEqual(self.item_bourbon.reorder_needed, Decimal('0.00'))

        # Gin: 2 * 32.00 = 64.00
        self.assertEqual(self.item_gin.total_value, Decimal('64.00'))
        self.assertTrue(self.item_gin.is_low_stock)
        self.assertEqual(self.item_gin.reorder_needed, Decimal('6.00')) # 8 - 2 = 6
        self.assertEqual(self.item_gin.suggested_cases_to_order, 1) # ceil(6 / 12) = 1
        self.assertEqual(self.item_gin.estimated_reorder_cost, Decimal('350.00'))

        # Beer: 10 * 1.85 = 18.50
        self.assertEqual(self.item_beer.total_value, Decimal('18.50'))
        self.assertTrue(self.item_beer.is_low_stock)
        self.assertEqual(self.item_beer.reorder_needed, Decimal('38.00')) # 48 - 10 = 38
        self.assertEqual(self.item_beer.suggested_cases_to_order, 2) # ceil(38 / 24) = 2
        self.assertEqual(self.item_beer.estimated_reorder_cost, Decimal('84.00')) # 2 * 42.00 = 84.00

    def test_bar_inventory_list_view(self):
        response = self.client.get(reverse('bar:inventory_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Maker&#x27;s Mark")
        self.assertContains(response, "LIQ-1001")
        self.assertContains(response, "Hendrick&#x27;s Gin")
        self.assertContains(response, "Pako&#x27;s IPA")
        self.assertContains(response, "Kraken Black Spiced Rum")
        self.assertContains(response, "Whisky")
        self.assertContains(response, "Dark Rum")
        self.assertContains(response, "Wyoming Wine &amp; Spirits Distributing")
        self.assertContains(response, "Snake River Beer Co")

    def test_bar_inventory_filter_by_tag(self):
        # Filter by Dark Rum tag
        response = self.client.get(reverse('bar:inventory_list') + f'?tag={self.tag_dark_rum.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kraken Black Spiced Rum")
        self.assertNotContains(response, "Maker&#x27;s Mark")
        self.assertNotContains(response, "Hendrick&#x27;s Gin")

    def test_bar_inventory_search_by_tag_name(self):
        # Search query matching tag 'whisky'
        response = self.client.get(reverse('bar:inventory_list') + '?q=whisky')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Maker&#x27;s Mark")
        self.assertNotContains(response, "Hendrick&#x27;s Gin")
        self.assertNotContains(response, "Snake River Pako&#x27;s IPA")

    def test_quick_add_tag_endpoint(self):
        response = self.client.post(reverse('bar:quick_add_tag'), {
            'name': 'Spiced Rum'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], 'Spiced Rum')
        self.assertTrue(BarItemTag.objects.filter(name='Spiced Rum').exists())

    def test_tag_list_endpoint(self):
        response = self.client.get(reverse('bar:tag_list'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        names = [t['name'] for t in data['tags']]
        self.assertIn('Dark Rum', names)
        self.assertIn('Whisky', names)
        self.assertIn('Rum', names)

    def test_bar_item_create_with_tags_and_custom_tags(self):
        response = self.client.post(reverse('bar:item_create'), {
            'stock_number': 'LIQ-1004',
            'description': 'Patron Silver Tequila 750ml',
            'category': 'liquor',
            'pricing_method': 'by_class',
            'beverage_class': 'top',
            'tags': [self.tag_whisky.pk], # Can pick existing tag
            'custom_tags': 'Tequila, Blanco', # And quick add new tags
            'on_hand': '8',
            'minimum_on_hand': '3',
            'single_price': '45.00',
            'case_price': '500.00',
            'sale_price': '15.00',
            'singles_per_case': 12,
            'distributor': self.distributor1.pk,
            'location': 'Main Bar',
            'unit_type': 'Bottle',
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        created_item = BarInventoryItem.objects.get(stock_number='LIQ-1004')
        item_tag_names = list(created_item.tags.values_list('name', flat=True))
        self.assertIn('Tequila', item_tag_names)
        self.assertIn('Blanco', item_tag_names)
        self.assertIn('Whisky', item_tag_names)

    def test_bar_inventory_filter_low_stock(self):
        response = self.client.get(reverse('bar:inventory_list') + '?stock_status=low')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hendrick&#x27;s Gin")
        self.assertContains(response, "Pako&#x27;s IPA")
        self.assertNotContains(response, "Maker&#x27;s Mark")

    def test_bar_item_detail_view(self):
        response = self.client.get(reverse('bar:item_detail', kwargs={'pk': self.item_bourbon.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Maker&#x27;s Mark")
        self.assertContains(response, "$513.00")
        self.assertContains(response, "$28.50")
        self.assertContains(response, "$310.00")
        self.assertContains(response, "Wyoming Wine &amp; Spirits Distributing")
        self.assertContains(response, "307-555-4400")

    def test_bar_item_create_view(self):
        response = self.client.post(reverse('bar:item_create'), {
            'stock_number': 'WNE-3001',
            'description': 'Cabernet Sauvignon 2021',
            'category': 'wine',
            'pricing_method': 'by_price',
            'on_hand': '24',
            'minimum_on_hand': '12',
            'single_price': '18.00',
            'case_price': '190.00',
            'sale_price': '45.00',
            'singles_per_case': 12,
            'distributor': self.distributor1.pk,
            'location': 'Wine Cellar',
            'unit_type': 'Bottle',
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(BarInventoryItem.objects.filter(stock_number='WNE-3001').exists())

    def test_bar_item_edit_view(self):
        response = self.client.post(reverse('bar:item_edit', kwargs={'pk': self.item_bourbon.pk}), {
            'stock_number': 'LIQ-1001',
            'description': 'Maker\'s Mark Kentucky Bourbon 750ml (Updated)',
            'category': 'liquor',
            'pricing_method': 'by_class',
            'beverage_class': 'top',
            'on_hand': '20',
            'minimum_on_hand': '6',
            'single_price': '29.00',
            'case_price': '315.00',
            'sale_price': '13.00',
            'singles_per_case': 12,
            'distributor': self.distributor1.pk,
            'location': 'Main Bar',
            'unit_type': 'Bottle',
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        self.item_bourbon.refresh_from_db()
        self.assertEqual(self.item_bourbon.on_hand, Decimal('20.00'))
        self.assertEqual(self.item_bourbon.total_value, Decimal('580.00'))

    def test_report_valuation(self):
        response = self.client.get(reverse('bar:report_valuation'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inventory Valuation Report")
        self.assertContains(response, "Spirits &amp; Liquor")
        self.assertContains(response, "Beer &amp; Cider")
        # Grand total valuation: 513.00 + 64.00 + 18.50 + 264.00 = 859.50
        self.assertContains(response, "$859.50")

    def test_report_low_stock(self):
        response = self.client.get(reverse('bar:report_low_stock'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Low Stock & Reorder Report")
        self.assertContains(response, "Wyoming Wine &amp; Spirits Distributing")
        self.assertContains(response, "307-555-4400")
        self.assertContains(response, "Snake River Beer Co")
        self.assertContains(response, "307-555-7711")
        self.assertContains(response, "Hendrick&#x27;s Gin")
        self.assertContains(response, "Pako&#x27;s IPA")
        self.assertNotContains(response, "Maker&#x27;s Mark")

    def test_report_distributors(self):
        response = self.client.get(reverse('bar:report_distributors'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Distributor Summary Report")
        self.assertContains(response, "Wyoming Wine &amp; Spirits Distributing")
        self.assertContains(response, "500 Distro Lane")
        self.assertContains(response, "Snake River Beer Co")

    def test_report_count_sheet(self):
        response = self.client.get(reverse('bar:report_count_sheet'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Physical Inventory Audit Worksheet")
        self.assertContains(response, "LIQ-1001")
        self.assertContains(response, "BER-2001")

    def test_pricing_methods_and_classes_model_properties(self):
        # 1. Top Shelf with sale price
        self.assertTrue(self.item_bourbon.is_by_class)
        self.assertTrue(self.item_bourbon.is_top_shelf)
        self.assertFalse(self.item_bourbon.is_by_price)
        self.assertEqual(self.item_bourbon.pricing_display, "Top Shelf ($14.50)")

        # 2. Call class
        self.assertTrue(self.item_gin.is_by_class)
        self.assertFalse(self.item_gin.is_top_shelf)
        self.assertEqual(self.item_gin.pricing_display, "Call")

        # 3. Domestic class
        self.assertTrue(self.item_beer.is_by_class)
        self.assertEqual(self.item_beer.pricing_display, "Domestic")

        # 4. Well class
        self.assertTrue(self.item_rum.is_by_class)
        self.assertEqual(self.item_rum.pricing_display, "Well")

        # 5. Import class
        item_import = BarInventoryItem.objects.create(
            stock_number="BER-2002",
            description="Guinness Extra Stout 12oz",
            category=BarInventoryItem.Category.BEER,
            pricing_method=BarInventoryItem.PricingMethod.BY_CLASS,
            beverage_class=BarInventoryItem.BeverageClass.IMPORT,
            on_hand=Decimal('24.00'),
            minimum_on_hand=Decimal('12.00'),
            single_price=Decimal('2.20'),
            case_price=Decimal('48.00'),
            sale_price=Decimal('0.00'),
            singles_per_case=24,
        )
        self.assertEqual(item_import.pricing_display, "Import")

        # 6. By Price
        item_by_price = BarInventoryItem.objects.create(
            stock_number="WNE-3002",
            description="Silver Oak Napa Valley Cabernet",
            category=BarInventoryItem.Category.WINE,
            pricing_method=BarInventoryItem.PricingMethod.BY_PRICE,
            on_hand=Decimal('6.00'),
            minimum_on_hand=Decimal('2.00'),
            single_price=Decimal('85.00'),
            case_price=Decimal('950.00'),
            sale_price=Decimal('165.00'),
            singles_per_case=12,
        )
        self.assertTrue(item_by_price.is_by_price)
        self.assertFalse(item_by_price.is_by_class)
        self.assertEqual(item_by_price.pricing_display, "$165.00")

    def test_create_item_sold_by_class_top_with_sale_price(self):
        response = self.client.post(reverse('bar:item_create'), {
            'stock_number': 'LIQ-5001',
            'description': 'Woodford Reserve Master Collection',
            'category': 'liquor',
            'pricing_method': 'by_class',
            'beverage_class': 'top',
            'on_hand': '4',
            'minimum_on_hand': '2',
            'single_price': '75.00',
            'case_price': '420.00',
            'sale_price': '22.00',
            'singles_per_case': 6,
            'location': 'Main Bar',
            'unit_type': 'Bottle',
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        item = BarInventoryItem.objects.get(stock_number='LIQ-5001')
        self.assertEqual(item.pricing_method, BarInventoryItem.PricingMethod.BY_CLASS)
        self.assertEqual(item.beverage_class, BarInventoryItem.BeverageClass.TOP)
        self.assertEqual(item.sale_price, Decimal('22.00'))

    def test_create_item_sold_by_price(self):
        response = self.client.post(reverse('bar:item_create'), {
            'stock_number': 'WNE-5002',
            'description': 'Caymus Special Selection Cabernet',
            'category': 'wine',
            'pricing_method': 'by_price',
            'on_hand': '6',
            'minimum_on_hand': '2',
            'single_price': '120.00',
            'case_price': '1350.00',
            'sale_price': '240.00',
            'singles_per_case': 12,
            'location': 'Wine Cellar',
            'unit_type': 'Bottle',
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        item = BarInventoryItem.objects.get(stock_number='WNE-5002')
        self.assertEqual(item.pricing_method, BarInventoryItem.PricingMethod.BY_PRICE)
        self.assertIsNone(item.beverage_class)
        self.assertEqual(item.sale_price, Decimal('240.00'))

    def test_form_validation_by_class_requires_class(self):
        response = self.client.post(reverse('bar:item_create'), {
            'stock_number': 'LIQ-5003',
            'description': 'Invalid Class Test Liquor',
            'category': 'liquor',
            'pricing_method': 'by_class',
            'beverage_class': '', # Missing beverage class
            'on_hand': '5',
            'minimum_on_hand': '2',
            'single_price': '20.00',
            'case_price': '200.00',
            'singles_per_case': 12,
            'is_active': True,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'beverage_class', 'Please select a class (Call, Well, Top Shelf, Domestic, or Import) when selling by class.')

    def test_inventory_filter_by_pricing_method_and_class(self):
        # Filter by class=top
        response = self.client.get(reverse('bar:inventory_list') + '?pricing_method=by_class&beverage_class=top')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Maker&#x27;s Mark")
        self.assertNotContains(response, "Hendrick&#x27;s Gin")
        self.assertNotContains(response, "Pako&#x27;s IPA")

        # Filter by class=call
        response_call = self.client.get(reverse('bar:inventory_list') + '?beverage_class=call')
        self.assertEqual(response_call.status_code, 200)
        self.assertContains(response_call, "Hendrick&#x27;s Gin")
        self.assertNotContains(response_call, "Maker&#x27;s Mark")
