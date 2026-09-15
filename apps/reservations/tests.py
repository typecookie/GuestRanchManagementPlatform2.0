from datetime import date
from django.test import TestCase
from apps.clients.models import Client, Household, HouseholdMember, TravelGroup, TravelGroupMember
from apps.reservations.models import Reservation, ReservationGuest


class ReservationGuestYearsDisplayTests(TestCase):
    def setUp(self):
        self.client_1 = Client.objects.create(
            first_name="Pat",
            last_name="Leonard"
        )
        self.reservation = Reservation.objects.create(
            reservation_name="Pat Leonard Stay",
            arrival_date=date(2026, 8, 30),
            departure_date=date(2026, 9, 6),
            primary_contact=self.client_1,
        )

    def test_years_display_from_notes(self):
        guest = ReservationGuest.objects.create(
            reservation=self.reservation,
            client=self.client_1,
            notes="18th year at Paradise\nDriving",
        )
        self.assertEqual(guest.years_display, "18th year")
        self.assertEqual(guest.years_count, 18)

    def test_years_display_from_notes_variations(self):
        guest = ReservationGuest.objects.create(
            reservation=self.reservation,
            client=self.client_1,
            notes="1st year at Paradise",
        )
        self.assertEqual(guest.years_display, "1st year")

        guest.notes = "2nd year"
        self.assertEqual(guest.years_display, "2nd year")

        guest.notes = "3rd year at Paradise"
        self.assertEqual(guest.years_display, "3rd year")

        guest.notes = "21st year at Paradise"
        self.assertEqual(guest.years_display, "21st year")

        guest.notes = "22nd year at Paradise"
        self.assertEqual(guest.years_display, "22nd year")

        guest.notes = "23rd year at Paradise"
        self.assertEqual(guest.years_display, "23rd year")

    def test_years_display_fallback_to_reservation_count(self):
        guest = ReservationGuest.objects.create(
            reservation=self.reservation,
            client=self.client_1,
            notes="Driving",
        )
        self.assertEqual(guest.years_display, "1st year")

    def test_hierarchical_years_resolution(self):
        # 1. TravelGroup default years return
        tg = TravelGroup.objects.create(name="Leonard Family Reunion", years_return=4)
        hh = Household.objects.create(name="Leonard Household", years_return=6)
        TravelGroupMember.objects.create(travel_group=tg, household=hh)

        c_inherited_all = Client.objects.create(first_name="Child", last_name="Leonard")
        HouseholdMember.objects.create(household=hh, client=c_inherited_all)

        c_explicit_client = Client.objects.create(first_name="Grandpa", last_name="Leonard", years_return=15)
        HouseholdMember.objects.create(household=hh, client=c_explicit_client)

        res_tg = Reservation.objects.create(
            reservation_name="Reunion Stay",
            arrival_date=date(2026, 8, 30),
            departure_date=date(2026, 9, 6),
            travel_group=tg,
            household=hh,
        )

        g_explicit = ReservationGuest.objects.create(reservation=res_tg, client=c_explicit_client)
        g_inherited = ReservationGuest.objects.create(reservation=res_tg, client=c_inherited_all)

        # Explicit client years override household and travel group
        self.assertEqual(g_explicit.years_count, 15)
        self.assertEqual(g_explicit.years_display, "15th year")

        # Blank client years inherit household years (6)
        self.assertEqual(g_inherited.years_count, 6)
        self.assertEqual(g_inherited.years_display, "6th year")

        # If household years_return is unset, inherits travel group (4)
        hh.years_return = None
        hh.save()
        self.assertEqual(g_inherited.years_count, 4)
        self.assertEqual(g_inherited.years_display, "4th year")
