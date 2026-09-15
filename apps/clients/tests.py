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
