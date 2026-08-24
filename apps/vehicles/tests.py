from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Vehicle, MaintenanceRecord
from apps.projects.models import Project

User = get_user_model()

class VehicleMaintenanceAndProjectsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="admin", password="password123", email="admin@ranch.local")
        self.client = Client()
        self.client.force_login(self.user)

        self.vehicle = Vehicle.objects.create(
            name="Ranch Truck #1",
            vehicle_type=Vehicle.VehicleType.TRUCK,
            make="Ford",
            model="F-250",
            year=2021,
        )

    def test_vehicle_maintenance_and_projects_display(self):
        project = Project.objects.create(
            name="Replace Brake Pads and Rotors",
            vehicle=self.vehicle,
            status=Project.Status.IN_PROGRESS,
            proposed_cost=300.00,
        )
        record = MaintenanceRecord.objects.create(
            vehicle=self.vehicle,
            issue="Oil Change & Filter",
            start_date="2026-08-01",
            diagnostics="Routine inspection completed",
            required_maintenance="Replace oil and oil filter",
        )

        response = self.client.get(reverse("vehicles:vehicle_detail", args=[self.vehicle.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Replace Brake Pads and Rotors")
        self.assertContains(response, "Oil Change &amp; Filter")
        self.assertContains(response, "+ New Project")
        self.assertContains(response, "+ New Maintenance Project")
        self.assertContains(response, "+ Log Maintenance")

        # Test project create view pre-population with vehicle
        form_resp = self.client.get(reverse("projects:project_create") + f"?vehicle={self.vehicle.pk}")
        self.assertEqual(form_resp.status_code, 200)
        self.assertContains(form_resp, f'value="{self.vehicle.pk}" selected')
