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


class DashboardRoutingAndOwnerPhotoSearchTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="ranch_admin",
            email="admin@ranch.local",
            password="password123",
        )
        self.owner_user = User.objects.create_user(
            username="ranch_owner_mom",
            email="mom@ranch.local",
            password="password123",
            first_name="Mom",
            last_name="Owner",
        )
        self.owner_user.profile.dashboard = "owner"
        self.owner_user.profile.save()

        self.client = Client()

    def test_default_user_routes_to_operations_dashboard(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Management Areas")
        self.assertContains(response, "Today at the Ranch")

    def test_owner_user_routes_to_owner_visual_dashboard(self):
        self.client.force_login(self.owner_user)
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visual Guest & Group Directory")
        self.assertContains(response, "Search Photos")

    def test_view_parameter_overrides_dashboard(self):
        # Admin user with view=owner
        self.client.force_login(self.admin_user)
        res_owner = self.client.get(f"{reverse('core:dashboard')}?view=owner")
        self.assertEqual(res_owner.status_code, 200)
        self.assertContains(res_owner, "Visual Guest & Group Directory")

        # Owner user with view=default
        self.client.force_login(self.owner_user)
        res_default = self.client.get(f"{reverse('core:dashboard')}?view=default")
        self.assertEqual(res_default.status_code, 200)
        self.assertContains(res_default, "Management Areas")

    def test_owner_photo_search_hierarchy_with_miller_group(self):
        from apps.clients.models import Client as RanchClient, Household, HouseholdMember, TravelGroup, TravelGroupMember

        self.client.force_login(self.owner_user)

        # 1. Travel group with 2 families: Miller Family and Davis Family
        tg = TravelGroup.objects.create(name="Miller & Friends Reunion", group_type="family_reunion")

        hh_miller = Household.objects.create(name="Miller Family")
        hh_davis = Household.objects.create(name="Davis Family")

        TravelGroupMember.objects.create(travel_group=tg, household=hh_miller)
        TravelGroupMember.objects.create(travel_group=tg, household=hh_davis)

        c_dad = RanchClient.objects.create(first_name="John", last_name="Miller", age=45)
        c_mom = RanchClient.objects.create(first_name="Jane", last_name="Miller", age=43)
        c_friend = RanchClient.objects.create(first_name="Sam", last_name="Davis", age=44)

        HouseholdMember.objects.create(household=hh_miller, client=c_dad, relationship="primary", is_primary_contact=True)
        HouseholdMember.objects.create(household=hh_miller, client=c_mom, relationship="spouse")
        HouseholdMember.objects.create(household=hh_davis, client=c_friend, relationship="primary", is_primary_contact=True)

        # 2. Standalone Miller household
        hh_standalone = Household.objects.create(name="Miller Grandparents")
        c_grandpa = RanchClient.objects.create(first_name="Robert", last_name="Miller", age=72)
        HouseholdMember.objects.create(household=hh_standalone, client=c_grandpa, relationship="primary")

        # 3. Standalone Miller client (individual traveler)
        c_solo = RanchClient.objects.create(first_name="Gregory", last_name="Miller", client_type="individual", age=28)

        # Search for "Miller"
        response = self.client.get(f"{reverse('core:dashboard')}?q=Miller")
        self.assertEqual(response.status_code, 200)
        
        # Verify Travel Group and both associated families + members are rendered
        self.assertContains(response, "Miller &amp; Friends Reunion")
        self.assertContains(response, "Miller Family")
        self.assertContains(response, "Davis Family")
        self.assertContains(response, "John Miller")
        self.assertContains(response, "Jane Miller")
        self.assertContains(response, "Sam Davis")

        # Verify Standalone Household and Standalone Client are rendered
        self.assertContains(response, "Miller Grandparents")
        self.assertContains(response, "Robert Miller")
        self.assertContains(response, "Gregory Miller")

        # Verify lightbox elements are present
        self.assertContains(response, "photoLightboxModal")
