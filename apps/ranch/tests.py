from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.cabins.models import Cabin
from apps.clients.models import Client as RanchClient, Household, TravelGroup
from apps.reservations.models import Reservation, ReservationGuest
from apps.horses.models import Horse, Saddle

User = get_user_model()


class WeeklyReportsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="ranchadmin",
            password="password123",
            email="admin@ranch.local"
        )
        self.client = Client()
        self.client.force_login(self.user)

        self.cabin = Cabin.objects.create(
            name="Honeymoon",
            capacity=2,
            sort_order=1
        )

        self.household = Household.objects.create(
            name="Holzworth Family",
            address_line_1="7648 Red Bay Court",
            city="Dublin",
            state="OH",
            postal_code="43016",
        )

        self.guest_client = RanchClient.objects.create(
            first_name="Brad",
            last_name="Holzworth",
            phone="614-571-4251",
            email="bradleyholzworth@gmail.com",
        )

        self.reservation_week1 = Reservation.objects.create(
            reservation_name="Holzworth Stay",
            household=self.household,
            primary_contact=self.guest_client,
            arrival_date=date(2026, 8, 30),
            departure_date=date(2026, 9, 6),
            adult_count=1,
            guest_count=1,
            status=Reservation.ReservationStatus.CONFIRMED,
        )

        self.res_guest_week1 = ReservationGuest.objects.create(
            reservation=self.reservation_week1,
            client=self.guest_client,
            cabin=self.cabin,
            notes="3rd year at Paradise\nDriving",
        )

        self.reservation_week2 = Reservation.objects.create(
            reservation_name="Holzworth Stay Week 2",
            household=self.household,
            primary_contact=self.guest_client,
            arrival_date=date(2026, 9, 6),
            departure_date=date(2026, 9, 13),
            adult_count=1,
            guest_count=1,
            status=Reservation.ReservationStatus.CONFIRMED,
        )

        self.res_guest_week2 = ReservationGuest.objects.create(
            reservation=self.reservation_week2,
            client=self.guest_client,
            cabin=self.cabin,
            notes="4th year at Paradise\nDriving",
        )

    def test_weekly_dining_guest_list_report(self):
        url = reverse("ranch:weekly_dining_guest_list_report")
        response = self.client.get(f"{url}?week=2026-08-30")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Brad Holzworth")
        self.assertContains(response, "3rd year")
        self.assertContains(response, "Dublin, OH")
        self.assertContains(response, "week=2026-08-23")
        self.assertContains(response, "week=2026-09-06")

        # Test week 2
        response_w2 = self.client.get(f"{url}?week=2026-09-06")
        self.assertEqual(response_w2.status_code, 200)
        self.assertContains(response_w2, "Brad Holzworth")
        self.assertContains(response_w2, "4th year")
        self.assertContains(response_w2, "Dublin, OH")
        self.assertContains(response_w2, "week=2026-08-30")
        self.assertContains(response_w2, "week=2026-09-13")

    def test_weekly_dining_guest_list_mixed_years_and_international_location(self):
        # Add another guest with same years (3rd year) and another guest with different years (1st year)
        connie = RanchClient.objects.create(
            first_name="Connie",
            last_name="Holzworth",
        )
        ReservationGuest.objects.create(
            reservation=self.reservation_week1,
            client=connie,
            cabin=self.cabin,
            notes="3rd year at Paradise",
        )
        tim = RanchClient.objects.create(
            first_name="Tim",
            last_name="Holzworth",
        )
        ReservationGuest.objects.create(
            reservation=self.reservation_week1,
            client=tim,
            cabin=self.cabin,
            notes="1st year at Paradise",
        )

        # Create international guest in another cabin
        cabin_intl = Cabin.objects.create(
            name="Ranger",
            capacity=2,
            sort_order=2
        )
        intl_household = Household.objects.create(
            name="Smith Family",
            city="Calgary",
            state="AB",
            country="Canada",
        )
        intl_client = RanchClient.objects.create(
            first_name="John",
            last_name="Smith",
        )
        intl_res = Reservation.objects.create(
            reservation_name="Smith Stay",
            household=intl_household,
            primary_contact=intl_client,
            arrival_date=date(2026, 8, 30),
            departure_date=date(2026, 9, 6),
            status=Reservation.ReservationStatus.CONFIRMED,
        )
        ReservationGuest.objects.create(
            reservation=intl_res,
            client=intl_client,
            cabin=cabin_intl,
            notes="2nd year at Paradise",
        )

        url = reverse("ranch:weekly_dining_guest_list_report")
        response = self.client.get(f"{url}?week=2026-08-30")
        self.assertEqual(response.status_code, 200)

        # Primary year for Holzworth party is 3rd year
        self.assertContains(response, "3rd year")
        self.assertContains(response, "Dublin, OH")

        # Tim has 1st year which is different, so 1st year appears inline next to his name
        content = response.content.decode("utf-8")
        self.assertIn("Tim Holzworth", content)
        self.assertIn("1st year", content)

        # Check international location
        self.assertContains(response, "John Smith")
        self.assertContains(response, "2nd year")
        self.assertContains(response, "Calgary, Canada")

    def test_weekly_dining_guest_list_report_travel_group_different_cabins(self):
        # Travel group with default 10 years, across Cabin 1 and Cabin 2
        cabin1 = Cabin.objects.create(name="Aspen Cabin", sort_order=15)
        cabin2 = Cabin.objects.create(name="Pine Cabin", sort_order=16)

        tg = TravelGroup.objects.create(name="Multi Cabin Travel Group", years_return=10)

        # Cabin 1 has guests with years [5, 12] -> Primary for Cabin 1 party should be 12th year (highest year of clients in that cabin)
        c1 = RanchClient.objects.create(first_name="Alice", last_name="Walker", years_return=5)
        c2 = RanchClient.objects.create(first_name="Bob", last_name="Walker", years_return=12)
        hh1 = Household.objects.create(name="Walker Family", primary_contact=c1)

        res1 = Reservation.objects.create(
            reservation_name="Walker Stay",
            primary_contact=c1,
            household=hh1,
            travel_group=tg,
            arrival_date=date(2026, 8, 30),
            departure_date=date(2026, 9, 6),
            status=Reservation.ReservationStatus.CONFIRMED,
        )
        ReservationGuest.objects.create(reservation=res1, client=c1, cabin=cabin1)
        ReservationGuest.objects.create(reservation=res1, client=c2, cabin=cabin1)

        # Cabin 2 has guests with no explicit client/household years -> inherits Travel Group (10 years)
        c3 = RanchClient.objects.create(first_name="Charlie", last_name="Walker")
        hh2 = Household.objects.create(name="Walker Branch", primary_contact=c3)

        res2 = Reservation.objects.create(
            reservation_name="Walker Branch Stay",
            primary_contact=c3,
            household=hh2,
            travel_group=tg,
            arrival_date=date(2026, 8, 30),
            departure_date=date(2026, 9, 6),
            status=Reservation.ReservationStatus.CONFIRMED,
        )
        ReservationGuest.objects.create(reservation=res2, client=c3, cabin=cabin2)

        url = reverse("ranch:weekly_dining_guest_list_report")
        response = self.client.get(f"{url}?week=2026-08-30")
        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")
        # In Aspen Cabin, highest client year is 12 -> 12th year as primary, Alice has 5th year inline
        self.assertIn("12th year", content)
        self.assertIn("5th year", content)

        # In Pine Cabin, inherits 10th year
        self.assertIn("10th year", content)

    def test_weekly_horse_assignment_report(self):
        url = reverse("ranch:weekly_horse_assignment_report")
        response = self.client.get(f"{url}?week=2026-08-30")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Brad Holzworth")
        self.assertContains(response, "week=2026-08-23")
        self.assertContains(response, "week=2026-09-06")

        response_w2 = self.client.get(f"{url}?week=2026-09-06")
        self.assertEqual(response_w2.status_code, 200)
        self.assertContains(response_w2, "Brad Holzworth")
        self.assertContains(response_w2, "week=2026-08-30")
        self.assertContains(response_w2, "week=2026-09-13")

    def test_weekly_special_requests_report(self):
        url = reverse("ranch:weekly_special_requests_report")
        response = self.client.get(f"{url}?week=2026-08-30")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Holzworth")
        self.assertContains(response, "week=2026-08-23")
        self.assertContains(response, "week=2026-09-06")

    def test_office_dashboard_tasks_week_by_week(self):
        # Create a horse and saddle to assign for week 1
        horse = Horse.objects.create(
            name="Spirit",
            breed="Mustang",
            status=Horse.Status.ACTIVE
        )
        saddle = Saddle.objects.create(
            saddle_number="S-101",
            rack_number="Rack 1",
            seat_size=15.5,
            min_stirrup_length=26,
            max_stirrup_length=34,
            status=Saddle.Status.IN_SERVICE
        )

        # Update res_guest_week1 with physical info and assignments
        self.res_guest_week1.horse = horse
        self.res_guest_week1.saddle = saddle
        self.res_guest_week1.height = "6'0\""
        self.res_guest_week1.weight = "180 lbs"
        self.res_guest_week1.riding_experience = ReservationGuest.RidingExperience.INTERMEDIATE
        self.res_guest_week1.signed_release = True
        self.res_guest_week1.save()

        self.reservation_week1.deposit_received = True
        self.reservation_week1.save()

        url = reverse("ranch:office_dashboard")
        response = self.client.get(f"{url}?week=2026-08-30")
        self.assertEqual(response.status_code, 200)

        # Check section headings
        self.assertContains(response, "Horse &amp; Saddle Assignments &amp; Rider Readiness")
        self.assertContains(response, "Guest Intake: Release &amp; Deposit Status")

        # Check single-card carousel controls
        self.assertContains(response, "task-card-carousel")
        self.assertContains(response, "card-week-toolbar")
        self.assertContains(response, "card-week-prev")
        self.assertContains(response, "card-week-next")
        self.assertContains(response, "card-week-pill")
        self.assertContains(response, "card-week-pane")

        # Check week 1 values
        self.assertContains(response, "Spirit")
        self.assertContains(response, "#S-101 (Rack 1)")
        self.assertContains(response, "Deposit Received")
        self.assertContains(response, "All Signed (1/1)")

        # Check week 2 values (missing horse/saddle/release/deposit)
        self.assertContains(response, "Deposit Needed")
        self.assertContains(response, "0/1 Signed")
        self.assertContains(response, "Unassigned Horse")
        self.assertContains(response, "Missing Height")

    def test_office_dashboard_booking_alerts(self):
        # Create a second cabin and two independent guests staying in the same cabin without a TravelGroup
        bear_paw = Cabin.objects.create(name="Bear Paw", capacity=4, sort_order=7)

        valek_client = RanchClient.objects.create(first_name="Karee", last_name="Valek")
        valek_res = Reservation.objects.create(
            reservation_name="Valek Stay",
            primary_contact=valek_client,
            arrival_date=date(2026, 8, 30),
            departure_date=date(2026, 9, 6),
            status=Reservation.ReservationStatus.CONFIRMED,
            guest_count=1,
        )
        ReservationGuest.objects.create(
            reservation=valek_res,
            client=valek_client,
            cabin=bear_paw,
        )

        wheeler_client = RanchClient.objects.create(first_name="Beth", last_name="Wheeler")
        wheeler_res = Reservation.objects.create(
            reservation_name="Wheeler Stay",
            primary_contact=wheeler_client,
            arrival_date=date(2026, 8, 30),
            departure_date=date(2026, 9, 6),
            status=Reservation.ReservationStatus.CONFIRMED,
            guest_count=1,
        )
        ReservationGuest.objects.create(
            reservation=wheeler_res,
            client=wheeler_client,
            cabin=bear_paw,
        )

        url = reverse("ranch:office_dashboard")
        response = self.client.get(f"{url}?week=2026-08-30")
        self.assertEqual(response.status_code, 200)

        # High-level alerts card and stat grid presence
        self.assertContains(response, "Data &amp; Booking Alerts (Operational Oddities)")
        self.assertContains(response, "Booking Alerts")
        self.assertContains(response, "alert-feed")

        # Specific alert for multiple reservations and ungrouped individuals in Bear Paw
        self.assertContains(response, "Multiple Reservations Sharing Cabin: Bear Paw")
        self.assertContains(response, "Cabin Shared Without Travel Group: Bear Paw")
        self.assertContains(response, "Create Both (Group Builder)")
        self.assertContains(response, "Create Travel Group")
        self.assertContains(response, "Create Household")
        self.assertContains(response, "/clients/group-builder/")

        # Verify that fixing the grouping (organizing them into a TravelGroup) clears the overlap warning
        tg_shared = TravelGroup.objects.create(name="Valek & Wheeler Shared Trip")
        valek_res.travel_group = tg_shared
        valek_res.save()
        wheeler_res.travel_group = tg_shared
        wheeler_res.save()

        resp_grouped = self.client.get(f"{url}?week=2026-08-30")
        self.assertEqual(resp_grouped.status_code, 200)
        self.assertNotContains(resp_grouped, "Multiple Reservations Sharing Cabin: Bear Paw")
        self.assertNotContains(resp_grouped, "Cabin Shared Without Travel Group: Bear Paw")

        # Test capacity overage alert
        small_cabin = Cabin.objects.create(name="Tiny Cabin", capacity=1, sort_order=20)
        guest_a = RanchClient.objects.create(first_name="Alex", last_name="Smith")
        guest_b = RanchClient.objects.create(first_name="Sam", last_name="Smith")
        over_res = Reservation.objects.create(
            reservation_name="Over Capacity Stay",
            primary_contact=guest_a,
            arrival_date=date(2026, 8, 30),
            departure_date=date(2026, 9, 6),
            status=Reservation.ReservationStatus.CONFIRMED,
        )
        ReservationGuest.objects.create(reservation=over_res, client=guest_a, cabin=small_cabin)
        ReservationGuest.objects.create(reservation=over_res, client=guest_b, cabin=small_cabin)

        resp_over = self.client.get(f"{url}?week=2026-08-30")
        self.assertEqual(resp_over.status_code, 200)
        self.assertContains(resp_over, "Cabin Over Capacity: Tiny Cabin")
        self.assertContains(resp_over, "exceeding its maximum capacity of 1")
