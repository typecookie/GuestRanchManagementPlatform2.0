from django.contrib.auth.models import User, Permission
from django.test import TestCase, Client
from django.urls import reverse


class NavigationSystemTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="nav_admin",
            email="nav_admin@ranch.local",
            password="password123",
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_dashboard_navigation_renders(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_department"], "dashboard")
        self.assertContains(response, "DEPARTMENTS")
        self.assertContains(response, "Office")
        self.assertContains(response, "Barn")
        self.assertContains(response, "Bar")
        self.assertContains(response, "Housekeeping")
        self.assertContains(response, "Maintenance")
        self.assertContains(response, "Admin")

    def test_office_department_navigation(self):
        response = self.client.get(reverse("ranch:office_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_department"], "office")
        self.assertContains(response, "Clients")
        self.assertContains(response, "Reservations")
        self.assertContains(response, "Cabins")
        self.assertContains(response, "Distributors & Contractors")
        self.assertContains(response, "Ranch Operations")

    def test_barn_department_navigation(self):
        response = self.client.get(reverse("horses:horse_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_department"], "barn")
        self.assertContains(response, "Horses")
        self.assertContains(response, "Pasture Board")
        self.assertContains(response, "Saddles")
        self.assertContains(response, "Distributors & Contractors")
        self.assertContains(response, "Ranch Operations")

    def test_bar_department_navigation(self):
        response = self.client.get(reverse("bar:inventory_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_department"], "bar")
        self.assertContains(response, "Bar Inventory")
        self.assertContains(response, "Distributors & Contractors")
        self.assertContains(response, "Ranch Operations")

    def test_housekeeping_department_navigation_excludes_contractors_and_operations(self):
        response = self.client.get(f"{reverse('cabins:cabin_list')}?dept=housekeeping")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_department"], "housekeeping")
        self.assertEqual(response.context["active_department_label"], "Housekeeping")
        self.assertContains(response, "Cabins")
        # Housekeeping must NOT have Distributors & Contractors or Ranch Operations
        subnav_html = response.content.decode("utf-8")
        # Isolate department-links container
        links_start = subnav_html.find('<div class="department-links">')
        links_end = subnav_html.find('</div>', links_start)
        dept_links_section = subnav_html[links_start:links_end]
        self.assertNotIn("Distributors & Contractors", dept_links_section)
        self.assertNotIn("Distributors &amp; Contractors", dept_links_section)
        self.assertNotIn("Ranch Operations", dept_links_section)

    def test_maintenance_department_navigation(self):
        response = self.client.get(f"{reverse('vehicles:vehicle_list')}?dept=maintenance")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_department"], "maintenance")
        self.assertContains(response, "Vehicles")
        self.assertContains(response, "Cabins")
        self.assertContains(response, "Projects")
        self.assertContains(response, "Distributors & Contractors")
        self.assertContains(response, "Ranch Operations")

    def test_admin_department_navigation(self):
        response = self.client.get(f"{reverse('reservations:operating_dates_list')}?dept=admin")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_department"], "admin")
        self.assertContains(response, "Operating Dates")
        self.assertContains(response, "Employees")
        self.assertContains(response, "User Management")
        self.assertContains(response, "Group Management")
        self.assertContains(response, "Admin")
        self.assertContains(response, "Distributors & Contractors")
        self.assertContains(response, "Ranch Operations")
