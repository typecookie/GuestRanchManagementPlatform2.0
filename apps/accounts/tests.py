from django.test import TestCase, Client
from django.contrib.auth import authenticate
from django.contrib.auth.models import User, Group, Permission
from django.urls import reverse
from apps.accounts.models import UserProfile
from apps.accounts.forms import UserForm, AdminUserPasswordChangeForm
from apps.groups.utils import set_module_permissions


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

    def test_user_list_contains_change_password_link(self):
        response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(response.status_code, 200)
        password_change_url = reverse("accounts:user_change_password", kwargs={"pk": self.staff_user.pk})
        self.assertContains(response, password_change_url)

    def test_user_edit_page_contains_change_password_link(self):
        response = self.client.get(reverse("accounts:user_update", kwargs={"pk": self.staff_user.pk}))
        self.assertEqual(response.status_code, 200)
        password_change_url = reverse("accounts:user_change_password", kwargs={"pk": self.staff_user.pk})
        self.assertContains(response, password_change_url)

    def test_admin_user_password_change_form_validation_and_saving(self):
        form_data = {
            "new_password1": "NewRanchSecret123!",
            "new_password2": "NewRanchSecret123!",
        }
        form = AdminUserPasswordChangeForm(user=self.staff_user, data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        # Check authentication succeeds with new password and fails with old
        self.assertIsNone(authenticate(username="staff_mom", password="password123"))
        self.assertIsNotNone(authenticate(username="staff_mom", password="NewRanchSecret123!"))

    def test_admin_user_password_change_form_mismatched_passwords(self):
        form_data = {
            "new_password1": "NewRanchSecret123!",
            "new_password2": "MismatchSecret999!",
        }
        form = AdminUserPasswordChangeForm(user=self.staff_user, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("new_password2", form.errors)

    def test_superuser_can_change_password_via_view(self):
        response = self.client.post(
            reverse("accounts:user_change_password", kwargs={"pk": self.staff_user.pk}),
            {
                "new_password1": "SuperAdminResetPass2026!",
                "new_password2": "SuperAdminResetPass2026!",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Password for user {self.staff_user.username} has been changed successfully.")

        # Authenticate and login with new credentials
        self.assertIsNone(authenticate(username="staff_mom", password="password123"))
        authenticated = authenticate(username="staff_mom", password="SuperAdminResetPass2026!")
        self.assertIsNotNone(authenticated)

    def test_ranch_admin_group_member_can_change_password(self):
        # Create ranch admin user with Ranch Admins group
        ranch_admin_group, _ = Group.objects.get_or_create(name="Ranch Admins")
        set_module_permissions(ranch_admin_group, "User Management", "write", True)

        ranch_admin_user = User.objects.create_user(
            username="ranch_admin_boss",
            email="boss@ranch.local",
            password="BossPassword2026!",
        )
        ranch_admin_user.groups.add(ranch_admin_group)

        admin_client = Client()
        admin_client.force_login(ranch_admin_user)

        response = admin_client.post(
            reverse("accounts:user_change_password", kwargs={"pk": self.staff_user.pk}),
            {
                "new_password1": "RanchAdminChangedPass789!",
                "new_password2": "RanchAdminChangedPass789!",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Password for user {self.staff_user.username} has been changed successfully.")

        # Verify new password works
        self.assertIsNone(authenticate(username="staff_mom", password="password123"))
        self.assertIsNotNone(authenticate(username="staff_mom", password="RanchAdminChangedPass789!"))

    def test_non_admin_user_cannot_change_password_for_users(self):
        unauthorized_user = User.objects.create_user(
            username="regular_wrangler",
            email="wrangler@ranch.local",
            password="WranglerPassword123!",
        )
        unauth_client = Client()
        unauth_client.force_login(unauthorized_user)

        # GET should be forbidden (403)
        response = unauth_client.get(reverse("accounts:user_change_password", kwargs={"pk": self.staff_user.pk}))
        self.assertEqual(response.status_code, 403)

        # POST should be forbidden (403)
        response = unauth_client.post(
            reverse("accounts:user_change_password", kwargs={"pk": self.staff_user.pk}),
            {
                "new_password1": "HackedPass123!",
                "new_password2": "HackedPass123!",
            },
        )
        self.assertEqual(response.status_code, 403)

        # Password remains unchanged
        self.assertIsNotNone(authenticate(username="staff_mom", password="password123"))

    def test_admin_can_change_own_password_and_remain_logged_in(self):
        response = self.client.post(
            reverse("accounts:user_change_password", kwargs={"pk": self.admin_user.pk}),
            {
                "new_password1": "BrandNewAdminPass2026!",
                "new_password2": "BrandNewAdminPass2026!",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Password for user {self.admin_user.username} has been changed successfully.")

        # Admin session remains valid (can still view protected pages)
        list_response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(list_response.status_code, 200)

        # New credentials authenticate successfully
        self.assertIsNotNone(authenticate(username="admin_user", password="BrandNewAdminPass2026!"))
