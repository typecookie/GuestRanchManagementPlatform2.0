from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Cabin, CabinInventoryItem, CabinInventoryMaintenanceLog
from apps.projects.models import Project

User = get_user_model()

class CabinInventoryAndMaintenanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="admin", password="password123", email="admin@ranch.local")
        self.client = Client()
        self.client.force_login(self.user)

        self.cabin = Cabin.objects.create(
            name="Pine Ridge Cabin",
            cabin_number="101",
            capacity=4,
            bed_configuration="1 King, 2 Twins",
            status=Cabin.CabinStatus.AVAILABLE,
        )

    def test_cabin_inventory_item_creation_and_detail(self):
        item = CabinInventoryItem.objects.create(
            cabin=self.cabin,
            name="Maytag Washing Machine",
            category=CabinInventoryItem.Category.APPLIANCE,
            brand="Maytag",
            model_number="MVW6200KW",
            serial_number="C8492048",
            location_in_cabin="Laundry Room",
            condition=CabinInventoryItem.Condition.GOOD,
            status=CabinInventoryItem.Status.OPERATIONAL,
        )

        response = self.client.get(reverse("cabins:cabin_detail", args=[self.cabin.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Maytag Washing Machine")
        self.assertContains(response, "Laundry Room")

        item_response = self.client.get(reverse("cabins:cabin_inventory_item_detail", args=[item.pk]))
        self.assertEqual(item_response.status_code, 200)
        self.assertContains(item_response, "MVW6200KW")
        self.assertContains(item_response, "C8492048")

    def test_cabin_inventory_maintenance_log_and_status_update(self):
        item = CabinInventoryItem.objects.create(
            cabin=self.cabin,
            name="Whirlpool Refrigerator",
            category=CabinInventoryItem.Category.APPLIANCE,
            status=CabinInventoryItem.Status.MAINTENANCE,
        )

        # Create maintenance log resolving the issue
        response = self.client.post(
            reverse("cabins:cabin_item_maintenance_log_create", args=[item.pk]),
            {
                "date": timezone.now().date(),
                "title": "Replaced Defrost Thermostat",
                "performed_by": "Appliance Pro Tech",
                "cost": "150.00",
                "status_update": CabinInventoryMaintenanceLog.StatusUpdate.OPERATIONAL,
                "work_performed": "Installed new thermostat and verified temperature regulation.",
                "notes": "Working normally now.",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.status, CabinInventoryItem.Status.OPERATIONAL)
        self.assertEqual(item.maintenance_logs.count(), 1)
        self.assertEqual(item.maintenance_logs.first().title, "Replaced Defrost Thermostat")

    def test_project_linking_to_cabin_and_cabin_item(self):
        item = CabinInventoryItem.objects.create(
            cabin=self.cabin,
            name="LG AC Unit",
            category=CabinInventoryItem.Category.APPLIANCE,
        )

        project = Project.objects.create(
            name="AC Unit Duct and Motor Replacement",
            cabin=self.cabin,
            cabin_item=item,
            status=Project.Status.IN_PROGRESS,
            proposed_cost=450.00,
        )

        cabin_resp = self.client.get(reverse("cabins:cabin_detail", args=[self.cabin.pk]))
        self.assertEqual(cabin_resp.status_code, 200)
        self.assertContains(cabin_resp, "AC Unit Duct and Motor Replacement")

        item_resp = self.client.get(reverse("cabins:cabin_inventory_item_detail", args=[item.pk]))
        self.assertEqual(item_resp.status_code, 200)
        self.assertContains(item_resp, "AC Unit Duct and Motor Replacement")

        proj_resp = self.client.get(reverse("projects:project_detail", args=[project.pk]))
        self.assertEqual(proj_resp.status_code, 200)
        self.assertContains(proj_resp, "Pine Ridge Cabin")
        self.assertContains(proj_resp, "LG AC Unit")
