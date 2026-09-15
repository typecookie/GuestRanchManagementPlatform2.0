from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from apps.contractors.models import Contractor


class ContractorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="adminuser",
            password="password123",
            email="admin@guestranch.com"
        )
        self.client.login(username="adminuser", password="password123")

        self.distributor = Contractor.objects.create(
            name="Rocky Mountain Beverages",
            contact_name="Sarah Connor",
            category=Contractor.Category.DISTRIBUTOR,
            phone="307-555-0199",
            email="orders@rockymountainbev.com",
            address_line_1="100 Mountain View Rd",
            city="Jackson",
            state="WY",
            postal_code="83001"
        )

        self.contractor = Contractor.objects.create(
            name="Apex Electric & HVAC",
            contact_name="Bob Vance",
            category=Contractor.Category.CONTRACTOR,
            phone="307-555-0144",
            email="bob@apexelectric.com",
            address_line_1="450 Industrial Parkway",
            city="Cody",
            state="WY",
            postal_code="82414"
        )

    def test_contractor_model_properties(self):
        self.assertEqual(str(self.distributor), "Rocky Mountain Beverages")
        self.assertIn("100 Mountain View Rd", self.distributor.full_address)
        self.assertIn("Jackson, WY 83001", self.distributor.full_address)

    def test_contractor_list_view(self):
        response = self.client.get(reverse('contractors:contractor_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rocky Mountain Beverages")
        self.assertContains(response, "Apex Electric &amp; HVAC")
        self.assertContains(response, "307-555-0199")

    def test_contractor_list_filter_category(self):
        response = self.client.get(reverse('contractors:contractor_list') + '?category=distributor')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rocky Mountain Beverages")
        self.assertNotContains(response, "Apex Electric &amp; HVAC")

    def test_contractor_detail_view(self):
        response = self.client.get(reverse('contractors:contractor_detail', kwargs={'pk': self.distributor.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rocky Mountain Beverages")
        self.assertContains(response, "Sarah Connor")
        self.assertContains(response, "307-555-0199")
        self.assertContains(response, "100 Mountain View Rd")

    def test_contractor_create_view(self):
        response = self.client.post(reverse('contractors:contractor_create'), {
            'name': 'High Country Spirits',
            'contact_name': 'Dave Miller',
            'category': 'distributor',
            'phone': '307-555-9988',
            'email': 'dave@highcountry.com',
            'address_line_1': '789 Elk St',
            'city': 'Dubois',
            'state': 'WY',
            'postal_code': '82513',
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Contractor.objects.filter(name='High Country Spirits').exists())

    def test_contractor_edit_view(self):
        response = self.client.post(reverse('contractors:contractor_edit', kwargs={'pk': self.distributor.pk}), {
            'name': 'Rocky Mountain Beverages LLC',
            'contact_name': 'Sarah Connor',
            'category': 'distributor',
            'phone': '307-555-0199',
            'email': 'orders@rockymountainbev.com',
            'address_line_1': '100 Mountain View Rd',
            'city': 'Jackson',
            'state': 'WY',
            'postal_code': '83001',
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        self.distributor.refresh_from_db()
        self.assertEqual(self.distributor.name, 'Rocky Mountain Beverages LLC')

    def test_contractor_delete_view(self):
        pk = self.contractor.pk
        response = self.client.post(reverse('contractors:contractor_delete', kwargs={'pk': pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Contractor.objects.filter(pk=pk).exists())

    def test_quick_add_contractor(self):
        response = self.client.post(reverse('contractors:quick_add_contractor'), {
            'name': 'Grand Teton Brewing',
            'phone': '307-555-3322',
            'category': 'distributor',
            'city': 'Victor',
            'state': 'ID',
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('id', data)
        self.assertEqual(data['name'], 'Grand Teton Brewing')
        self.assertTrue(Contractor.objects.filter(name='Grand Teton Brewing').exists())
