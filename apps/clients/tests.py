import json
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from apps.cabins.models import Cabin
from apps.clients.models import Client as RanchClient, Household, HouseholdMember, TravelGroup, TravelGroupMember
from apps.reservations.models import Reservation, ReservationGuest

User = get_user_model()


class GroupBuilderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="testadmin",
            password="password123",
            email="admin@ranch.local"
        )
        self.client = Client()
        self.client.force_login(self.user)

        self.c1 = RanchClient.objects.create(
            first_name="Karee",
            last_name="Valek",
            email="kvalek@example.com",
            phone="303-555-0101",
        )
        self.c2 = RanchClient.objects.create(
            first_name="Beth",
            last_name="Wheeler",
            email="bwheeler@example.com",
            phone="303-555-0102",
        )
        self.c3 = RanchClient.objects.create(
            first_name="Bob",
            last_name="Wheeler",
            email="bobwheeler@example.com",
            phone="303-555-0103",
        )

        self.cabin = Cabin.objects.create(name="Bear Paw", capacity=4, sort_order=7)

        self.reservation = Reservation.objects.create(
            reservation_name="Bear Paw Shared Stay",
            primary_contact=self.c1,
            arrival_date=date(2026, 8, 30),
            departure_date=date(2026, 9, 6),
            status=Reservation.ReservationStatus.CONFIRMED,
            guest_count=3,
        )
        ReservationGuest.objects.create(reservation=self.reservation, client=self.c1, cabin=self.cabin)
        ReservationGuest.objects.create(reservation=self.reservation, client=self.c2, cabin=self.cabin)
        ReservationGuest.objects.create(reservation=self.reservation, client=self.c3, cabin=self.cabin)

    def test_group_builder_get_modes(self):
        url = reverse("clients:group_builder")

        # Mode both
        resp_both = self.client.get(f"{url}?mode=both&reservation_id={self.reservation.id}&clients={self.c1.id},{self.c2.id}")
        self.assertEqual(resp_both.status_code, 200)
        self.assertContains(resp_both, "Create Travel Group &amp; Households")
        self.assertContains(resp_both, "Karee Valek")
        self.assertContains(resp_both, "Beth Wheeler")
        self.assertContains(resp_both, "households-canvas")

        # Verify all JSON embedded script blocks are valid JSON
        import re
        script_matches = re.findall(r'<script type="application/json" id="([^"]+)">([\s\S]*?)</script>', resp_both.content.decode("utf-8"))
        self.assertGreater(len(script_matches), 0)
        for script_id, json_content in script_matches:
            try:
                parsed = json.loads(json_content.strip())
                self.assertIsNotNone(parsed)
            except Exception as err:
                self.fail(f"Script #{script_id} content is not valid JSON: {err}\nContent:\n{json_content}")

        # Mode household
        resp_hh = self.client.get(f"{url}?mode=household&name=Wheeler%20Family")
        self.assertEqual(resp_hh.status_code, 200)
        self.assertContains(resp_hh, "Create Household")
        self.assertContains(resp_hh, "single-hh-drop-zone")

        # Mode travel_group
        resp_tg = self.client.get(f"{url}?mode=travel_group&name=Ranch%20Reunion")
        self.assertEqual(resp_tg.status_code, 200)
        self.assertContains(resp_tg, "Create Travel Group")
        self.assertContains(resp_tg, "tg-only-drop-zone")

    def test_group_builder_post_both_multiple_households(self):
        url = reverse("clients:group_builder")

        households_data = [
            {
                "name": "Valek Family",
                "address_line_1": "100 Valek Trail",
                "city": "Denver",
                "state": "CO",
                "postal_code": "80202",
                "years_return": 8,
                "primary_contact_id": self.c1.id,
                "billing_contact_id": self.c1.id,
                "clients": [
                    {"id": self.c1.id, "relationship": "self"}
                ]
            },
            {
                "name": "Wheeler Family",
                "address_line_1": "200 Wheeler Way",
                "city": "Boulder",
                "state": "CO",
                "postal_code": "80301",
                "years_return": 3,
                "primary_contact_id": self.c2.id,
                "billing_contact_id": self.c2.id,
                "clients": [
                    {"id": self.c2.id, "relationship": "self"},
                    {"id": self.c3.id, "relationship": "spouse"}
                ]
            }
        ]

        post_payload = {
            "mode": "both",
            "travel_group_name": "Valek & Wheeler Shared Trip",
            "group_type": "multi_family_trip",
            "travel_group_years_return": "5",
            "travel_group_notes": "Staying together in Bear Paw cabin",
            "reservation_id": str(self.reservation.id),
            "households": json.dumps(households_data),
            "direct_clients": "[]",
        }

        response = self.client.post(url, post_payload)
        self.assertEqual(response.status_code, 302)

        # Verify created entities in database
        tg = TravelGroup.objects.filter(name="Valek & Wheeler Shared Trip").first()
        self.assertIsNotNone(tg)
        self.assertEqual(tg.group_type, TravelGroup.GroupType.MULTI_FAMILY_TRIP)
        self.assertEqual(tg.years_return, 5)

        # Check households
        valek_hh = Household.objects.filter(name="Valek Family").first()
        wheeler_hh = Household.objects.filter(name="Wheeler Family").first()
        self.assertIsNotNone(valek_hh)
        self.assertIsNotNone(wheeler_hh)
        self.assertEqual(valek_hh.years_return, 8)
        self.assertEqual(wheeler_hh.years_return, 3)

        # Check memberships in households
        self.assertEqual(HouseholdMember.objects.filter(household=valek_hh).count(), 1)
        self.assertEqual(HouseholdMember.objects.filter(household=wheeler_hh).count(), 2)
        self.assertEqual(valek_hh.primary_contact, self.c1)
        self.assertEqual(wheeler_hh.primary_contact, self.c2)

        # Check TravelGroupMemberships
        tg_members = TravelGroupMember.objects.filter(travel_group=tg)
        self.assertEqual(tg_members.count(), 2)
        hh_ids = set(tg_members.values_list("household_id", flat=True))
        self.assertIn(valek_hh.id, hh_ids)
        self.assertIn(wheeler_hh.id, hh_ids)

        # Verify reservation was updated with the travel group and matching household
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.travel_group, tg)
        self.assertEqual(self.reservation.household, valek_hh)

    def test_group_builder_post_household(self):
        url = reverse("clients:group_builder")

        clients_data = [
            {"id": self.c2.id, "relationship": "self"},
            {"id": self.c3.id, "relationship": "spouse"},
        ]

        post_payload = {
            "mode": "household",
            "household_name": "Wheeler Household",
            "address_line_1": "55 Aspen Court",
            "city": "Steamboat Springs",
            "state": "CO",
            "postal_code": "80487",
            "country": "United States",
            "notes": "Loves horseback riding",
            "primary_contact_id": str(self.c2.id),
            "reservation_id": str(self.reservation.id),
            "clients": json.dumps(clients_data),
        }

        response = self.client.post(url, post_payload)
        self.assertEqual(response.status_code, 302)

        hh = Household.objects.filter(name="Wheeler Household").first()
        self.assertIsNotNone(hh)
        self.assertEqual(hh.city, "Steamboat Springs")
        self.assertEqual(hh.primary_contact, self.c2)
        self.assertEqual(HouseholdMember.objects.filter(household=hh).count(), 2)

        # Verify reservation household updated
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.household, hh)

    def test_group_builder_post_travel_group(self):
        url = reverse("clients:group_builder")

        clients_data = [
            {"id": self.c1.id, "role": "primary_organizer"},
            {"id": self.c2.id, "role": "guest"},
        ]

        post_payload = {
            "mode": "travel_group",
            "travel_group_name": "Autumn Trail Riders",
            "group_type": "friend_group",
            "notes": "Group of friends visiting together",
            "reservation_id": str(self.reservation.id),
            "clients": json.dumps(clients_data),
        }

        response = self.client.post(url, post_payload)
        self.assertEqual(response.status_code, 302)

        tg = TravelGroup.objects.filter(name="Autumn Trail Riders").first()
        self.assertIsNotNone(tg)
        self.assertEqual(tg.group_type, TravelGroup.GroupType.FRIEND_GROUP)
        self.assertEqual(TravelGroupMember.objects.filter(travel_group=tg).count(), 2)

        # Verify reservation travel group updated
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.travel_group, tg)

    def test_group_builder_context_linked_from_cabin(self):
        url = reverse("clients:group_builder")
        resp = self.client.get(f"{url}?mode=both&cabin_id={self.cabin.id}&clients={self.c1.id},{self.c2.id},{self.c3.id}&name=Bear%20Paw%20Group")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Context Linked")
        self.assertContains(resp, "Bear Paw")
        self.assertContains(resp, "3 Offending/Party Guests Auto-Populated")
        self.assertContains(resp, "Bear Paw Group")

    def test_group_builder_links_multiple_cabin_sharing_reservations(self):
        # Create two distinct reservations sharing Bear Paw cabin
        res1 = Reservation.objects.create(
            reservation_name="Valek Solo Stay",
            primary_contact=self.c1,
            arrival_date=date(2026, 8, 30),
            departure_date=date(2026, 9, 6),
            status=Reservation.ReservationStatus.CONFIRMED,
            guest_count=1,
        )
        ReservationGuest.objects.create(reservation=res1, client=self.c1, cabin=self.cabin)

        res2 = Reservation.objects.create(
            reservation_name="Wheeler Couple Stay",
            primary_contact=self.c2,
            arrival_date=date(2026, 8, 30),
            departure_date=date(2026, 9, 6),
            status=Reservation.ReservationStatus.CONFIRMED,
            guest_count=2,
        )
        ReservationGuest.objects.create(reservation=res2, client=self.c2, cabin=self.cabin)
        ReservationGuest.objects.create(reservation=res2, client=self.c3, cabin=self.cabin)

        url = reverse("clients:group_builder")
        households_data = [
            {
                "name": "Valek Household",
                "primary_contact_id": self.c1.id,
                "clients": [{"id": self.c1.id, "relationship": "self"}]
            },
            {
                "name": "Wheeler Household",
                "primary_contact_id": self.c2.id,
                "clients": [
                    {"id": self.c2.id, "relationship": "self"},
                    {"id": self.c3.id, "relationship": "spouse"}
                ]
            }
        ]

        post_payload = {
            "mode": "both",
            "travel_group_name": "Bear Paw Combined Group",
            "cabin_id": str(self.cabin.id),
            "households": json.dumps(households_data),
            "direct_clients": "[]",
        }

        resp = self.client.post(url, post_payload)
        self.assertEqual(resp.status_code, 302)

        tg = TravelGroup.objects.filter(name="Bear Paw Combined Group").first()
        valek_hh = Household.objects.filter(name="Valek Household").first()
        wheeler_hh = Household.objects.filter(name="Wheeler Household").first()

        res1.refresh_from_db()
        res2.refresh_from_db()

        self.assertEqual(res1.travel_group, tg)
        self.assertEqual(res1.household, valek_hh)
        self.assertEqual(res2.travel_group, tg)
        self.assertEqual(res2.household, wheeler_hh)


class ClientRiderProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="ranchmanager",
            password="password123",
            email="manager@ranch.local",
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_client_rider_and_physical_fields_creation(self):
        client = RanchClient.objects.create(
            first_name="Clint",
            last_name="Eastwood",
            email="clint@example.com",
            phone="307-555-0199",
            is_rider=True,
            riding_level=RanchClient.RidingLevel.ADVANCED,
            height="6'4\"",
            weight="205 lbs",
            saddle_preference="16\" Highback Roper",
            rider_notes="Prefers energetic horses, great balance on steep trails.",
        )

        self.assertEqual(client.height, "6'4\"")
        self.assertEqual(client.weight, "205 lbs")
        self.assertTrue(client.is_rider)
        self.assertEqual(client.saddle_preference, "16\" Highback Roper")
        self.assertIn("energetic horses", client.rider_notes)

    def test_client_create_and_update_views_with_rider_data(self):
        create_url = reverse("clients:client_create")
        post_data = {
            "first_name": "Sarah",
            "last_name": "Connor",
            "email": "sarah@example.com",
            "phone": "555-0100",
            "client_type": RanchClient.ClientType.ADULT,
            "is_rider": True,
            "riding_level": RanchClient.RidingLevel.INTERMEDIATE,
            "height": "5'6\"",
            "weight": "135 lbs",
            "saddle_preference": "15\" Western Trail Saddle",
            "rider_notes": "Experienced with calm geldings",
            "is_active": True,
        }

        resp = self.client.post(create_url, post_data)
        self.assertEqual(resp.status_code, 302)

        client = RanchClient.objects.get(email="sarah@example.com")
        self.assertEqual(client.height, "5'6\"")
        self.assertEqual(client.weight, "135 lbs")
        self.assertEqual(client.saddle_preference, "15\" Western Trail Saddle")
        self.assertEqual(client.rider_notes, "Experienced with calm geldings")

        # View Client Detail page
        detail_url = reverse("clients:client_detail", args=[client.pk])
        detail_resp = self.client.get(detail_url)
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, "Rider &amp; Physical Information")
        self.assertContains(detail_resp, "5&#x27;6&quot;")
        self.assertContains(detail_resp, "135 lbs")
        self.assertContains(detail_resp, "15&quot; Western Trail Saddle")
        self.assertContains(detail_resp, "Experienced with calm geldings")
        self.assertContains(detail_resp, "Active Rider")

        # View Client List page
        list_url = reverse("clients:client_list")
        list_resp = self.client.get(list_url)
        self.assertEqual(list_resp.status_code, 200)
        self.assertContains(list_resp, "5&#x27;6&quot;")
        self.assertContains(list_resp, "135 lbs")

    def test_reservation_guest_auto_populates_physical_data_from_client(self):
        rider_client = RanchClient.objects.create(
            first_name="Wyatt",
            last_name="Earp",
            email="wyatt@example.com",
            is_rider=True,
            riding_level=RanchClient.RidingLevel.ADVANCED,
            height="6'0\"",
            weight="190 lbs",
        )

        res = Reservation.objects.create(
            reservation_name="Earp Stay",
            primary_contact=rider_client,
            arrival_date=date(2026, 7, 5),
            departure_date=date(2026, 7, 12),
            status=Reservation.ReservationStatus.CONFIRMED,
        )

        # Create ReservationGuest without explicitly providing height & weight
        guest = ReservationGuest.objects.create(
            reservation=res,
            client=rider_client,
        )

        # Should auto-populate from client profile on save
        self.assertEqual(guest.height, "6'0\"")
        self.assertEqual(guest.weight, "190 lbs")
        self.assertEqual(guest.riding_experience, ReservationGuest.RidingExperience.ADVANCED)
        self.assertTrue(guest.is_riding)
        self.assertEqual(guest.effective_height, "6'0\"")
        self.assertEqual(guest.effective_weight, "190 lbs")

    def test_client_delete_safe_without_reservations(self):
        # Client without reservations can be permanently deleted
        orphan_client = RanchClient.objects.create(
            first_name="Orphan",
            last_name="Guest",
            email="orphan@example.com",
        )
        hh = Household.objects.create(name="Orphan Family")
        HouseholdMember.objects.create(household=hh, client=orphan_client)

        self.assertTrue(orphan_client.can_delete)

        # GET confirm delete page
        del_url = reverse("clients:client_delete", args=[orphan_client.pk])
        resp = self.client.get(del_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Safe to Delete")
        self.assertContains(resp, "Permanently Delete Client")

        # POST delete
        post_resp = self.client.post(del_url, {"action": "delete"})
        self.assertRedirects(post_resp, reverse("clients:client_list"))
        self.assertFalse(RanchClient.objects.filter(pk=orphan_client.pk).exists())
        self.assertFalse(HouseholdMember.objects.filter(client=orphan_client).exists())

    def test_client_delete_blocked_and_archives_when_linked_to_reservation_guest(self):
        # Client with reservation history cannot be deleted and is archived instead
        stay_client = RanchClient.objects.create(
            first_name="Stay",
            last_name="Guest",
            email="stay@example.com",
            is_active=True,
        )
        res = Reservation.objects.create(
            reservation_name="Summer Stay 2026",
            arrival_date=date(2026, 7, 5),
            departure_date=date(2026, 7, 12),
        )
        guest = ReservationGuest.objects.create(
            reservation=res,
            client=stay_client,
        )

        self.assertFalse(stay_client.can_delete)

        # GET confirm delete page
        del_url = reverse("clients:client_delete", args=[stay_client.pk])
        resp = self.client.get(del_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Data Integrity Notice")
        self.assertContains(resp, "Archive Client")

        # POST delete attempt -> automatically archives instead of deleting
        post_resp = self.client.post(del_url, {"action": "delete"})
        self.assertRedirects(post_resp, reverse("clients:client_list"))

        stay_client.refresh_from_db()
        self.assertTrue(RanchClient.objects.filter(pk=stay_client.pk).exists())
        self.assertFalse(stay_client.is_active)
        self.assertTrue(ReservationGuest.objects.filter(pk=guest.pk).exists())

    def test_client_delete_blocked_when_primary_contact_on_reservation(self):
        contact_client = RanchClient.objects.create(
            first_name="Leader",
            last_name="Primary",
            email="leader@example.com",
            is_active=True,
        )
        res = Reservation.objects.create(
            reservation_name="Leader Reunion",
            primary_contact=contact_client,
            arrival_date=date(2026, 8, 1),
            departure_date=date(2026, 8, 8),
        )

        self.assertFalse(contact_client.can_delete)

        del_url = reverse("clients:client_delete", args=[contact_client.pk])
        post_resp = self.client.post(del_url, {"action": "delete"})
        self.assertRedirects(post_resp, reverse("clients:client_list"))

        contact_client.refresh_from_db()
        self.assertFalse(contact_client.is_active)
        res.refresh_from_db()
        self.assertEqual(res.primary_contact, contact_client)

    def test_client_toggle_archive_and_restore(self):
        client = RanchClient.objects.create(
            first_name="Active",
            last_name="Person",
            is_active=True,
        )
        toggle_url = reverse("clients:client_toggle_archive", args=[client.pk])

        # Archive client
        resp = self.client.post(toggle_url)
        self.assertRedirects(resp, reverse("clients:client_detail", args=[client.pk]))
        client.refresh_from_db()
        self.assertFalse(client.is_active)

        # Detail view shows archived badge and restore button
        detail_resp = self.client.get(reverse("clients:client_detail", args=[client.pk]))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, "Archived")
        self.assertContains(detail_resp, "Restore Client")

        # Restore client
        resp2 = self.client.post(toggle_url)
        self.assertRedirects(resp2, reverse("clients:client_detail", args=[client.pk]))
        client.refresh_from_db()
        self.assertTrue(client.is_active)

    def test_client_sex_choices_and_stay_referencing(self):
        # 1. Test male client
        male_client = RanchClient.objects.create(
            first_name="John",
            last_name="Wayne",
            sex=RanchClient.Sex.MALE,
        )
        self.assertEqual(male_client.sex, "male")
        self.assertEqual(male_client.get_sex_display(), "Male")

        # 2. Test female client
        female_client = RanchClient.objects.create(
            first_name="Annie",
            last_name="Oakley",
            sex=RanchClient.Sex.FEMALE,
        )
        self.assertEqual(female_client.sex, "female")
        self.assertEqual(female_client.get_sex_display(), "Female")

        # 3. Test other client
        other_client = RanchClient.objects.create(
            first_name="Alex",
            last_name="Taylor",
            sex=RanchClient.Sex.OTHER,
        )
        self.assertEqual(other_client.sex, "other")
        self.assertEqual(other_client.get_sex_display(), "Other")

        # 4. Test stay record property referencing
        res = Reservation.objects.create(
            reservation_name="Western Heritage Stay",
            arrival_date=date(2026, 6, 1),
            departure_date=date(2026, 6, 8),
        )
        guest_female = ReservationGuest.objects.create(
            reservation=res,
            client=female_client,
        )
        self.assertEqual(guest_female.sex, "female")
        self.assertEqual(guest_female.effective_sex, "female")
        self.assertEqual(guest_female.get_sex_display(), "Female")

    def test_client_form_and_views_with_sex(self):
        # Create client via form with sex=female
        create_url = reverse("clients:client_create")
        post_data = {
            "first_name": "Clara",
            "last_name": "Clayton",
            "email": "clara@example.com",
            "phone": "555-1234",
            "date_of_birth": "1990-05-15",
            "sex": "female",
            "client_type": RanchClient.ClientType.ADULT,
            "is_rider": True,
            "riding_level": RanchClient.RidingLevel.BEGINNER,
            "is_active": True,
        }
        resp = self.client.post(create_url, post_data)
        self.assertEqual(resp.status_code, 302)

        client = RanchClient.objects.get(email="clara@example.com")
        self.assertEqual(client.sex, "female")

        # Check detail view displays sex
        detail_resp = self.client.get(reverse("clients:client_detail", args=[client.pk]))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, "Female")

        # Update client sex to other
        edit_url = reverse("clients:client_update", args=[client.pk])
        post_data["sex"] = "other"
        resp_update = self.client.post(edit_url, post_data)
        self.assertEqual(resp_update.status_code, 302)
        client.refresh_from_db()
        self.assertEqual(client.sex, "other")

        # Test client list filtering by sex
        list_url = reverse("clients:client_list")
        resp_list = self.client.get(list_url, {"sex": "other"})
        self.assertEqual(resp_list.status_code, 200)
        self.assertContains(resp_list, "Clara")

        resp_list_male = self.client.get(list_url, {"sex": "male"})
        self.assertEqual(resp_list_male.status_code, 200)
        self.assertNotContains(resp_list_male, "Clara Clayton")

    def test_client_age_calculation_and_fallback(self):
        # 1. Client with Date of Birth auto-calculates age
        today = date.today()
        dob = date(today.year - 30, today.month, today.day)
        client_with_dob = RanchClient.objects.create(
            first_name="Alice",
            last_name="Smith",
            date_of_birth=dob,
        )
        self.assertEqual(client_with_dob.age, 30)
        self.assertEqual(client_with_dob.effective_age, 30)
        self.assertEqual(client_with_dob.calculated_age, 30)

        # 2. Client without DOB but with explicit age
        client_with_age_only = RanchClient.objects.create(
            first_name="Bob",
            last_name="Jones",
            age=45,
        )
        self.assertIsNone(client_with_age_only.date_of_birth)
        self.assertEqual(client_with_age_only.age, 45)
        self.assertEqual(client_with_age_only.effective_age, 45)
        self.assertEqual(client_with_age_only.calculated_age, 45)

        # 3. Reservation guest uses client.effective_age when DOB is missing
        res = Reservation.objects.create(
            reservation_name="Jones Ranch Trip",
            arrival_date=date(2026, 7, 10),
            departure_date=date(2026, 7, 17),
        )
        guest = ReservationGuest.objects.create(
            reservation=res,
            client=client_with_age_only,
        )
        self.assertEqual(guest.age_at_stay, 45)
        self.assertEqual(guest.effective_age, 45)
        self.assertEqual(guest.effective_age_at_stay, 45)

        # 4. Form submission with age only
        create_url = reverse("clients:client_create")
        post_data = {
            "first_name": "Charlie",
            "last_name": "Brown",
            "email": "charlie@example.com",
            "age": 12,
            "client_type": RanchClient.ClientType.CHILD,
            "is_rider": True,
            "riding_level": RanchClient.RidingLevel.BEGINNER,
            "is_active": True,
        }
        resp = self.client.post(create_url, post_data)
        self.assertEqual(resp.status_code, 302)

        client_created = RanchClient.objects.get(email="charlie@example.com")
        self.assertIsNone(client_created.date_of_birth)
        self.assertEqual(client_created.age, 12)
        self.assertEqual(client_created.effective_age, 12)

        # 5. Detail view display
        detail_resp = self.client.get(reverse("clients:client_detail", args=[client_created.pk]))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, "12")
        self.assertContains(detail_resp, "Direct Entry")

        # Detail view for client with DOB
        detail_resp_dob = self.client.get(reverse("clients:client_detail", args=[client_with_dob.pk]))
        self.assertEqual(detail_resp_dob.status_code, 200)
        self.assertContains(detail_resp_dob, "30")
        self.assertContains(detail_resp_dob, "Calculated from DOB")
