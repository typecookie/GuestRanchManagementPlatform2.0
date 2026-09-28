from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.horses.models import Horse, Pasture, Saddle, MedicalRecord
from apps.horses.forms import HorseForm, PastureForm

User = get_user_model()


class PastureModelTests(TestCase):
    def setUp(self):
        self.pasture_north = Pasture.objects.create(
            name="North Pasture",
            description="40 acres with creek",
            display_order=1
        )
        self.pasture_south = Pasture.objects.create(
            name="South Pasture",
            description="20 acres flat meadow",
            display_order=2
        )
        self.horse = Horse.objects.create(
            name="Thunder",
            breed="Mustang",
            gender=Horse.Gender.GELDING,
            status=Horse.Status.ACTIVE,
            pasture=self.pasture_north
        )

    def test_pasture_creation_and_str(self):
        self.assertEqual(str(self.pasture_north), "North Pasture")
        self.assertEqual(self.pasture_north.horses.count(), 1)
        self.assertEqual(self.pasture_south.horses.count(), 0)

    def test_can_be_deleted_property(self):
        # North pasture contains a horse -> cannot be deleted
        self.assertFalse(self.pasture_north.can_be_deleted())
        # South pasture is empty -> can be deleted
        self.assertTrue(self.pasture_south.can_be_deleted())

    def test_delete_pasture_with_horses_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self.pasture_north.delete()
        # Verify pasture was NOT deleted
        self.assertTrue(Pasture.objects.filter(pk=self.pasture_north.pk).exists())

    def test_delete_empty_pasture_succeeds(self):
        pasture_id = self.pasture_south.pk
        self.pasture_south.delete()
        self.assertFalse(Pasture.objects.filter(pk=pasture_id).exists())


class PastureBoardViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="adminuser",
            password="adminpassword",
            email="admin@ranch.local"
        )
        self.client = TestClient()
        self.client.force_login(self.user)

        self.pasture1 = Pasture.objects.create(name="East Pasture", display_order=1)
        self.pasture2 = Pasture.objects.create(name="West Pasture", display_order=2)

        self.horse_assigned = Horse.objects.create(
            name="Blaze",
            breed="Arabian",
            gender=Horse.Gender.MARE,
            status=Horse.Status.ACTIVE,
            pasture=self.pasture1
        )
        self.horse_unassigned = Horse.objects.create(
            name="Shadow",
            breed="Quarter Horse",
            gender=Horse.Gender.GELDING,
            status=Horse.Status.ACTIVE,
            pasture=None
        )

    def test_pasture_board_requires_authentication(self):
        anon_client = TestClient()
        response = anon_client.get(reverse("horses:pasture_board"))
        self.assertEqual(response.status_code, 302)

    def test_pasture_board_renders_successfully(self):
        response = self.client.get(reverse("horses:pasture_board"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "horses/pasture_board.html")
        self.assertContains(response, "East Pasture")
        self.assertContains(response, "West Pasture")
        self.assertContains(response, "Blaze")
        self.assertContains(response, "Shadow")
        self.assertContains(response, "Unassigned / Barn")

    def test_pasture_board_search_filter(self):
        response = self.client.get(reverse("horses:pasture_board") + "?q=Blaze")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Blaze")
        self.assertNotContains(response, "Shadow")


class PastureCRUDViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="ranchmanager",
            password="password123",
            email="mgr@ranch.local"
        )
        self.client = TestClient()
        self.client.force_login(self.user)

        self.pasture_with_horse = Pasture.objects.create(name="Main Field")
        self.horse = Horse.objects.create(
            name="Comet",
            pasture=self.pasture_with_horse
        )
        self.empty_pasture = Pasture.objects.create(name="Empty Field")

    def test_pasture_create_standard(self):
        response = self.client.post(reverse("horses:pasture_create"), {
            "name": "Foal Pasture",
            "description": "Safe fenced pasture",
            "display_order": 5
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Pasture.objects.filter(name="Foal Pasture").exists())

    def test_pasture_create_ajax(self):
        response = self.client.post(
            reverse("horses:pasture_create"),
            {
                "name": "River Run Pasture",
                "description": "Near the river",
                "display_order": 3
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["name"], "River Run Pasture")
        self.assertTrue(Pasture.objects.filter(name="River Run Pasture").exists())

    def test_pasture_update_view(self):
        response = self.client.post(
            reverse("horses:pasture_update", args=[self.empty_pasture.pk]),
            {
                "name": "Renamed Empty Field",
                "description": "Updated notes",
                "display_order": 10
            }
        )
        self.assertEqual(response.status_code, 302)
        self.empty_pasture.refresh_from_db()
        self.assertEqual(self.empty_pasture.name, "Renamed Empty Field")

    def test_pasture_delete_empty_succeeds(self):
        response = self.client.post(
            reverse("horses:pasture_delete", args=[self.empty_pasture.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Pasture.objects.filter(pk=self.empty_pasture.pk).exists())

    def test_pasture_delete_ajax_empty_succeeds(self):
        target = Pasture.objects.create(name="Temporary Pen")
        response = self.client.post(
            reverse("horses:pasture_delete", args=[target.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertFalse(Pasture.objects.filter(pk=target.pk).exists())

    def test_pasture_delete_with_horses_is_blocked_standard(self):
        response = self.client.post(
            reverse("horses:pasture_delete", args=[self.pasture_with_horse.pk])
        )
        self.assertEqual(response.status_code, 302)
        # Verify pasture is still intact
        self.assertTrue(Pasture.objects.filter(pk=self.pasture_with_horse.pk).exists())

    def test_pasture_delete_with_horses_is_blocked_ajax(self):
        response = self.client.post(
            reverse("horses:pasture_delete", args=[self.pasture_with_horse.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("Cannot remove pasture", data["message"])
        # Verify pasture is still intact
        self.assertTrue(Pasture.objects.filter(pk=self.pasture_with_horse.pk).exists())


class UpdateHorsePastureViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="ranchlead",
            password="password123",
            email="lead@ranch.local"
        )
        self.client = TestClient()
        self.client.force_login(self.user)

        self.pasture_a = Pasture.objects.create(name="Pasture A")
        self.pasture_b = Pasture.objects.create(name="Pasture B")
        self.horse = Horse.objects.create(
            name="Starlight",
            breed="Paint",
            pasture=self.pasture_a
        )

    def test_move_horse_to_another_pasture(self):
        response = self.client.post(
            reverse("horses:update_horse_pasture", args=[self.horse.pk]),
            {"pasture_id": self.pasture_b.pk},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["pasture_id"], self.pasture_b.pk)
        self.assertEqual(data["pasture_name"], "Pasture B")

        self.horse.refresh_from_db()
        self.assertEqual(self.horse.pasture, self.pasture_b)

    def test_move_horse_to_unassigned(self):
        response = self.client.post(
            reverse("horses:update_horse_pasture", args=[self.horse.pk]),
            {"pasture_id": ""},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIsNone(data["pasture_id"])
        self.assertEqual(data["pasture_name"], "Unassigned")

        self.horse.refresh_from_db()
        self.assertIsNone(self.horse.pasture)


class HorseIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="superuser",
            password="password",
            email="super@ranch.local"
        )
        self.client = TestClient()
        self.client.force_login(self.user)

        self.pasture = Pasture.objects.create(name="Hill Pasture")
        self.horse = Horse.objects.create(
            name="Apollo",
            breed="Appaloosa",
            gender=Horse.Gender.GELDING,
            status=Horse.Status.ACTIVE,
            pasture=self.pasture
        )
        self.unassigned_horse = Horse.objects.create(
            name="Barnaby",
            breed="Clydesdale",
            gender=Horse.Gender.GELDING,
            status=Horse.Status.ACTIVE,
            pasture=None
        )

    def test_horse_list_filtering_by_pasture(self):
        # Filter by specific pasture
        response = self.client.get(reverse("horses:horse_list") + f"?pasture={self.pasture.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apollo")
        self.assertNotContains(response, "Barnaby")

        # Filter by unassigned
        response_unassigned = self.client.get(reverse("horses:horse_list") + "?pasture=unassigned")
        self.assertEqual(response_unassigned.status_code, 200)
        self.assertContains(response_unassigned, "Barnaby")
        self.assertNotContains(response_unassigned, "Apollo")

    def test_horse_detail_shows_pasture(self):
        response = self.client.get(reverse("horses:horse_detail", args=[self.horse.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hill Pasture")

    def test_horse_form_saves_pasture(self):
        form_data = {
            "name": "Dakota",
            "breed": "Quarter Horse",
            "gender": Horse.Gender.MARE,
            "status": Horse.Status.ACTIVE,
            "pasture": self.pasture.pk,
            "notes": "Gentle trail horse",
            "medical_notes": ""
        }
        form = HorseForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        horse = form.save()
        self.assertEqual(horse.pasture, self.pasture)
