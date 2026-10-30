from django.test import TestCase, Client
from django.contrib.auth import authenticate
from django.contrib.auth.models import User, Group
from django.urls import reverse
from apps.accounts.models import UserProfile
from apps.accounts.forms import UserForm


class UserProfileAndDashboardSettingsTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin_user",
            email="admin@ranch.local",
            password="password123",
        )
        self.staff_user = User.objects.create_user(
            username="staff_mom",
            email="mom@ranch.local",
            password="password123",
            first_name="Mom",
            last_name="Owner",
        )
        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_user_profile_automatically_created_on_user_save(self):
        self.assertTrue(hasattr(self.staff_user, "profile"))
        self.assertEqual(self.staff_user.profile.dashboard, UserProfile.DASHBOARD_DEFAULT)

    def test_user_form_updates_dashboard_selection(self):
        form_data = {
            "username": "staff_mom",
            "first_name": "Mom",
            "last_name": "Owner",
            "email": "mom@ranch.local",
            "dashboard": UserProfile.DASHBOARD_OWNER,
            "is_active": True,
        }
        form = UserForm(data=form_data, instance=self.staff_user)
        self.assertTrue(form.is_valid(), form.errors)
        saved_user = form.save()
        
        self.staff_user.refresh_from_db()
        self.assertEqual(self.staff_user.profile.dashboard, UserProfile.DASHBOARD_OWNER)

    def test_user_list_view_shows_dashboard_badges(self):
        self.staff_user.profile.dashboard = UserProfile.DASHBOARD_OWNER
        self.staff_user.profile.save()

        response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Owner Visual")
        self.assertContains(response, "Operations")

    def test_new_user_creation_hashes_password_and_allows_login(self):
        # Create a new user through UserForm
        form_data = {
            "username": "new_ranch_hand",
            "first_name": "Jake",
            "last_name": "Wrangler",
            "email": "jake@ranch.local",
            "password": "SecurePassword999!",
            "dashboard": UserProfile.DASHBOARD_DEFAULT,
            "is_active": True,
        }
        form = UserForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        # Check authentication succeeds
        authenticated_user = authenticate(username="new_ranch_hand", password="SecurePassword999!")
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user.id, user.id)

        # Check login succeeds via client
        guest_client = Client()
        login_success = guest_client.login(username="new_ranch_hand", password="SecurePassword999!")
        self.assertTrue(login_success)

    def test_new_user_creation_via_view_hashes_password_and_allows_login(self):
        # POST to user_create view
        response = self.client.post(
            reverse("accounts:user_create"),
            {
                "username": "sarah_cook",
                "first_name": "Sarah",
                "last_name": "Baker",
                "email": "sarah@ranch.local",
                "password": "ChefPassword2026!",
                "dashboard": UserProfile.DASHBOARD_DEFAULT,
                "is_active": "on",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        # Authenticate and login with new credentials
        authenticated_user = authenticate(username="sarah_cook", password="ChefPassword2026!")
        self.assertIsNotNone(authenticated_user)

        guest_client = Client()
        login_success = guest_client.login(username="sarah_cook", password="ChefPassword2026!")
        self.assertTrue(login_success)

    def test_user_update_does_not_require_or_show_password_field(self):
        form = UserForm(instance=self.staff_user)
        self.assertNotIn("password", form.fields)

        form_data = {
            "username": "staff_mom",
            "first_name": "Mother",
            "last_name": "Owner",
            "email": "mom@ranch.local",
            "dashboard": UserProfile.DASHBOARD_OWNER,
            "is_active": True,
        }
        form = UserForm(data=form_data, instance=self.staff_user)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        # Original password still works
        authenticated_user = authenticate(username="staff_mom", password="password123")
        self.assertIsNotNone(authenticated_user)

    def test_user_update_via_view_saves_changes_without_password(self):
        response = self.client.post(
            reverse("accounts:user_update", kwargs={"pk": self.staff_user.pk}),
            {
                "username": "staff_mom",
                "first_name": "Mother",
                "last_name": "Owner Updated",
                "email": "mom_updated@ranch.local",
                "dashboard": UserProfile.DASHBOARD_OWNER,
                "is_active": "on",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.staff_user.refresh_from_db()
        self.assertEqual(self.staff_user.last_name, "Owner Updated")
        self.assertEqual(self.staff_user.email, "mom_updated@ranch.local")

        # Original password still intact
        authenticated_user = authenticate(username="staff_mom", password="password123")
        self.assertIsNotNone(authenticated_user)
