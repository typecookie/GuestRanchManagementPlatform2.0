from datetime import date, timedelta
from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import site
from apps.cabins.models import Cabin
from apps.clients.models import Client, Household, HouseholdMember, TravelGroup, TravelGroupMember
from apps.reservations.models import OperatingSeason, Reservation, ReservationFlight, ReservationGuest
from apps.reservations.forms import OperatingSeasonForm, ReservationFlightForm, ReservationForm
from apps.reservations.season_utils import (
    get_default_season_dates,
    is_date_open,
    is_week_open,
    get_active_season_for_date,
    get_current_or_upcoming_season,
    get_default_grid_year_month,
    ensure_default_operating_season,
)

User = get_user_model()


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


class OperatingSeasonModelAndUtilsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="adminuser",
            password="password123",
            email="admin@ranch.local",
        )
        self.client = TestClient()
        self.client.force_login(self.user)

    def test_default_season_dates(self):
        start_d, end_d = get_default_season_dates(2026)
        self.assertEqual(start_d, date(2026, 6, 1))
        self.assertEqual(end_d, date(2026, 9, 30))

    def test_is_date_open_with_defaults(self):
        # When no seasons are in the database, June to September are open
        self.assertTrue(is_date_open(date(2026, 6, 1)))
        self.assertTrue(is_date_open(date(2026, 7, 15)))
        self.assertTrue(is_date_open(date(2026, 9, 30)))
        self.assertFalse(is_date_open(date(2026, 5, 31)))
        self.assertFalse(is_date_open(date(2026, 10, 1)))
        self.assertFalse(is_date_open(date(2026, 1, 15)))

    def test_is_week_open_with_defaults(self):
        # A week spanning May 31 to June 7 overlaps with June, so it is open
        self.assertTrue(is_week_open(date(2026, 5, 31), date(2026, 6, 7)))
        # A week in January is closed
        self.assertFalse(is_week_open(date(2026, 1, 4), date(2026, 1, 11)))

    def test_operating_season_model_properties_and_methods(self):
        season = OperatingSeason.objects.create(
            name="Summer 2026",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 9, 30),
            is_active=True,
        )
        self.assertEqual(season.duration_days, 122)
        self.assertEqual(season.duration_weeks, 17.4)
        self.assertTrue(season.contains_date(date(2026, 7, 4)))
        self.assertFalse(season.contains_date(date(2026, 10, 15)))
        self.assertTrue(season.overlaps_week(date(2026, 5, 31), date(2026, 6, 7)))
        self.assertFalse(season.overlaps_week(date(2026, 10, 4), date(2026, 10, 11)))

    def test_operating_season_validation(self):
        season = OperatingSeason(
            name="Invalid Season",
            start_date=date(2026, 9, 30),
            end_date=date(2026, 6, 1),
        )
        with self.assertRaises(ValidationError):
            season.clean()

    def test_custom_season_overrides_defaults(self):
        # Create a custom season from July 1 to August 31
        OperatingSeason.objects.create(
            name="Short Season",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 8, 31),
            is_active=True,
        )
        self.assertFalse(is_date_open(date(2026, 6, 15)))
        self.assertTrue(is_date_open(date(2026, 7, 15)))
        self.assertTrue(is_date_open(date(2026, 8, 20)))
        self.assertFalse(is_date_open(date(2026, 9, 10)))

    def test_inactive_season_ignored(self):
        OperatingSeason.objects.create(
            name="Cancelled Season",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 8, 31),
            is_active=False,
        )
        # Because no active season exists, fallback to default June-September
        self.assertTrue(is_date_open(date(2026, 6, 15)))

    def test_ensure_default_operating_season(self):
        season = ensure_default_operating_season(2026)
        self.assertEqual(season.name, "Summer Season 2026")
        self.assertEqual(season.start_date, date(2026, 6, 1))
        self.assertEqual(season.end_date, date(2026, 9, 30))

        # Idempotent call
        season2 = ensure_default_operating_season(2026)
        self.assertEqual(season.pk, season2.pk)

    def test_get_default_grid_year_month(self):
        # Date in season returns its own month
        y, m = get_default_grid_year_month(date(2026, 7, 10))
        self.assertEqual((y, m), (2026, 7))

        # Date off-season returns season start month (June)
        y, m = get_default_grid_year_month(date(2026, 2, 10))
        self.assertEqual((y, m), (2026, 6))


class OperatingDatesViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="ranchadmin",
            password="password123",
            email="admin@ranch.local",
        )
        self.client = TestClient()
        self.client.force_login(self.user)

        self.cabin = Cabin.objects.create(
            name="Eagle View",
            capacity=4,
            sort_order=1,
            is_active=True,
        )

    def test_operating_dates_list_view(self):
        url = reverse("reservations:operating_dates_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operating Dates & Seasons")
        self.assertContains(response, "June 1 – Sept 30")

    def test_operating_season_create_view(self):
        url = reverse("reservations:operating_season_create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        post_data = {
            "name": "Summer 2026 Custom",
            "start_date": "2026-06-01",
            "end_date": "2026-09-30",
            "is_active": True,
            "notes": "Main guest season",
        }
        post_response = self.client.post(url, post_data)
        self.assertEqual(post_response.status_code, 302)
        self.assertTrue(OperatingSeason.objects.filter(name="Summer 2026 Custom").exists())

    def test_operating_season_update_view(self):
        season = OperatingSeason.objects.create(
            name="Summer 2026 Initial",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 9, 30),
            is_active=True,
        )
        url = reverse("reservations:operating_season_update", args=[season.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        post_data = {
            "name": "Summer 2026 Extended",
            "start_date": "2026-05-25",
            "end_date": "2026-10-05",
            "is_active": True,
            "notes": "Extended season",
        }
        post_response = self.client.post(url, post_data)
        self.assertEqual(post_response.status_code, 302)
        season.refresh_from_db()
        self.assertEqual(season.name, "Summer 2026 Extended")
        self.assertEqual(season.start_date, date(2026, 5, 25))

    def test_operating_season_delete_view(self):
        season = OperatingSeason.objects.create(
            name="To Delete",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 9, 30),
            is_active=True,
        )
        url = reverse("reservations:operating_season_delete", args=[season.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        post_response = self.client.post(url)
        self.assertEqual(post_response.status_code, 302)
        self.assertFalse(OperatingSeason.objects.filter(pk=season.pk).exists())

    def test_operating_season_reset_defaults_view(self):
        url = reverse("reservations:operating_season_reset_defaults")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        today_year = date.today().year
        self.assertTrue(OperatingSeason.objects.filter(start_date=date(today_year, 6, 1), end_date=date(today_year, 9, 30)).exists())

    def test_reservation_grid_closed_weeks_and_filtering(self):
        # By default filter_closed is ON (True)
        grid_url = reverse("reservations:reservation_grid")
        response_jan_default = self.client.get(f"{grid_url}?year=2026&month=1")
        self.assertEqual(response_jan_default.status_code, 200)
        self.assertTrue(response_jan_default.context["filter_closed"])
        self.assertEqual(len(response_jan_default.context["weeks"]), 0)
        self.assertContains(response_jan_default, "All Weeks Closed in January 2026")
        self.assertContains(response_jan_default, "Show Closed / Off-Season Weeks")

        # Explicitly disable filter_closed (filter_closed=false) in January
        response_jan_all = self.client.get(f"{grid_url}?year=2026&month=1&filter_closed=false")
        self.assertEqual(response_jan_all.status_code, 200)
        self.assertFalse(response_jan_all.context["filter_closed"])
        self.assertGreater(len(response_jan_all.context["weeks"]), 0)
        self.assertContains(response_jan_all, "Off-Season")
        self.assertContains(response_jan_all, "Closed")

        # In July (open month, filter_closed is true by default)
        response_jul = self.client.get(f"{grid_url}?year=2026&month=7")
        self.assertEqual(response_jul.status_code, 200)
        self.assertTrue(response_jul.context["filter_closed"])
        self.assertGreater(len(response_jul.context["weeks"]), 0)
        self.assertContains(response_jul, "Open Month")

    def test_season_utils_skip_closed_weeks(self):
        from .season_utils import get_next_open_week, get_previous_open_week, get_open_weeks_sequence

        # End of 2026 default summer season (Sunday Sept 27, 2026 ends Oct 4 -> last week of season)
        late_sept = date(2026, 9, 27)
        next_open = get_next_open_week(late_sept)
        # Should skip October through May and jump to late May / early June 2027 (first open week of 2027 season)
        self.assertIn(next_open.month, [5, 6])
        self.assertEqual(next_open.year, 2027)

        # Stepping back from first open week of 2027 (May 30, 2027)
        first_week_2027 = date(2027, 5, 30)
        prev_open = get_previous_open_week(first_week_2027)
        # Should jump backwards past closed winter/spring months to late September 2026
        self.assertEqual(prev_open.year, 2026)
        self.assertEqual(prev_open.month, 9)

        # Sequence of 4 weeks starting from Sept 20, 2026
        seq = get_open_weeks_sequence(date(2026, 9, 20), num_weeks=4)
        self.assertEqual(len(seq), 4)
        self.assertEqual(seq[0], date(2026, 9, 20))
        self.assertEqual(seq[1], date(2026, 9, 27))
        self.assertEqual(seq[2].year, 2027)
        self.assertEqual(seq[3].year, 2027)

    def test_reservation_list_season_filter(self):
        # Create reservations: one in season (July), one off season (February)
        res_in = Reservation.objects.create(
            reservation_name="In-Season Guest",
            arrival_date=date(2026, 7, 5),
            departure_date=date(2026, 7, 12),
        )
        res_out = Reservation.objects.create(
            reservation_name="Off-Season Maintenance",
            arrival_date=date(2026, 2, 1),
            departure_date=date(2026, 2, 8),
        )

        list_url = reverse("reservations:reservation_list")

        # Filter by open_season
        response = self.client.get(f"{list_url}?season=open_season&show_past=true")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "In-Season Guest")
        self.assertNotContains(response, "Off-Season Maintenance")

    def test_prior_season_and_default_season_logic(self):
        from .season_utils import (
            get_default_season,
            get_categorized_seasons,
            get_next_open_month,
            get_previous_open_month,
            get_default_grid_year_month,
            is_month_open,
        )

        season_2025 = OperatingSeason.objects.create(
            name="Summer 2025",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 9, 30),
            is_active=True,
        )
        season_2026 = OperatingSeason.objects.create(
            name="Summer 2026",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 9, 30),
            is_active=True,
        )
        season_2027 = OperatingSeason.objects.create(
            name="Summer 2027",
            start_date=date(2027, 6, 1),
            end_date=date(2027, 9, 30),
            is_active=True,
        )

        # 1. Check during 2026 season (July 15, 2026)
        during_2026 = date(2026, 7, 15)
        self.assertTrue(season_2026.is_current(during_2026))
        self.assertFalse(season_2026.is_prior(during_2026))
        self.assertTrue(season_2025.is_prior(during_2026))
        self.assertTrue(season_2027.is_upcoming(during_2026))

        # Default season during 2026 season is 2026
        self.assertEqual(get_default_season(during_2026), season_2026)

        # 2. As soon as last day open passes (Oct 1, 2026):
        # 2026 is now a prior season!
        after_2026 = date(2026, 10, 1)
        self.assertTrue(season_2026.is_prior(after_2026))
        self.assertEqual(season_2026.status_label(after_2026), "Prior Season")
        self.assertFalse(season_2026.is_current(after_2026))

        # Default season as soon as 2026 passes is the NEXT season (2027)!
        self.assertEqual(get_default_season(after_2026), season_2027)

        # Grid landing defaults to Next Season (June 2027)
        grid_y, grid_m = get_default_grid_year_month(after_2026)
        self.assertEqual((grid_y, grid_m), (2027, 6))

        # Categorized seasons on Oct 1, 2026:
        cats = get_categorized_seasons(after_2026)
        self.assertEqual(cats["default_season"], season_2027)
        self.assertIn(season_2027, cats["current_and_upcoming"])
        self.assertIn(season_2026, cats["prior_seasons"])
        self.assertIn(season_2025, cats["prior_seasons"])

        # 3. Skipping closed months
        self.assertTrue(is_month_open(2026, 9))
        self.assertFalse(is_month_open(2026, 10))
        self.assertFalse(is_month_open(2027, 1))
        self.assertTrue(is_month_open(2027, 6))

        # Next open month from Sept 2026 skips Oct-May and returns June 2027
        next_open_y, next_open_m = get_next_open_month(2026, 9)
        self.assertEqual((next_open_y, next_open_m), (2027, 6))

        # Previous open month from June 2027 skips May-Oct and returns Sept 2026
        prev_open_y, prev_open_m = get_previous_open_month(2027, 6)
        self.assertEqual((prev_open_y, prev_open_m), (2026, 9))

    def test_reservation_grid_season_selection_and_navigation(self):
        season_2025 = OperatingSeason.objects.create(
            name="Summer 2025",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 9, 30),
            is_active=True,
        )
        season_2026 = OperatingSeason.objects.create(
            name="Summer 2026",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 9, 30),
            is_active=True,
        )

        grid_url = reverse("reservations:reservation_grid")

        # Select season via query param
        response = self.client.get(f"{grid_url}?season={season_2025.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["year"], 2025)
        self.assertEqual(response.context["month"], 6)
        self.assertEqual(response.context["current_season"], season_2025)
        self.assertContains(response, "Summer 2025")

        # Month navigation from Sept 2026 skips closed months
        response_sept = self.client.get(f"{grid_url}?year=2026&month=9")
        self.assertEqual(response_sept.status_code, 200)
        self.assertEqual(response_sept.context["next_year"], 2027)
        self.assertEqual(response_sept.context["next_month"], 6)

    def test_reservation_grid_cabin_capacity_ordering(self):
        # Create cabins with varying capacities
        Cabin.objects.all().delete()
        c_large = Cabin.objects.create(name="Grand Lodge", capacity=12, sort_order=1, is_active=True)
        c_tiny = Cabin.objects.create(name="Solo Hideaway", capacity=1, sort_order=2, is_active=True)
        c_mid = Cabin.objects.create(name="Family Duplex", capacity=6, sort_order=1, is_active=True)
        c_small = Cabin.objects.create(name="Couple Cabin", capacity=2, sort_order=1, is_active=True)

        grid_url = reverse("reservations:reservation_grid")
        response = self.client.get(f"{grid_url}?year=2026&month=7")
        self.assertEqual(response.status_code, 200)

        grid_cabins = [row["cabin"] for row in response.context["grid_rows"]]
        self.assertEqual(grid_cabins, [c_tiny, c_small, c_mid, c_large])
        # Verify rendered HTML shows capacity indicators
        self.assertContains(response, "Cap: 1")
        self.assertContains(response, "Cap: 12")

    def test_open_months_sequence(self):
        from apps.reservations.season_utils import get_open_months_sequence
        OperatingSeason.objects.create(
            name="Summer 2026",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 9, 30),
            is_active=True,
        )
        OperatingSeason.objects.create(
            name="Summer 2027",
            start_date=date(2027, 6, 1),
            end_date=date(2027, 9, 30),
            is_active=True,
        )

        # 4 open months starting in June 2026 -> June, July, Aug, Sept 2026
        seq = get_open_months_sequence(date(2026, 6, 1), num_months=4)
        self.assertEqual(len(seq), 4)
        self.assertEqual([(m["year"], m["month"]) for m in seq], [
            (2026, 6), (2026, 7), (2026, 8), (2026, 9)
        ])

        # 4 open months starting in August 2026 -> Aug 2026, Sept 2026, skips winter, June 2027, July 2027
        seq_cross = get_open_months_sequence(date(2026, 8, 1), num_months=4)
        self.assertEqual([(m["year"], m["month"]) for m in seq_cross], [
            (2026, 8), (2026, 9), (2027, 6), (2027, 7)
        ])

    def test_admin_registration(self):
        self.assertIn(OperatingSeason, site._registry)
        self.assertIn(ReservationFlight, site._registry)


class ReservationTravelAndFlightTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="ranchstaff",
            password="password123",
            email="staff@ranch.local",
        )
        self.client = TestClient()
        self.client.force_login(self.user)

        self.contact = Client.objects.create(
            first_name="Jane",
            last_name="Doe",
            email="jane.doe@example.com",
        )
        self.reservation = Reservation.objects.create(
            reservation_name="Doe Family Vacation",
            arrival_date=date(2026, 7, 5),
            departure_date=date(2026, 7, 12),
            primary_contact=self.contact,
            is_driving=True,
            driving_notes="Arriving by SUV around 3pm",
            is_flying=True,
            flying_notes="Flying United, shuttle requested from CPR",
        )

    def test_reservation_travel_fields_model(self):
        self.assertTrue(self.reservation.is_driving)
        self.assertEqual(self.reservation.driving_notes, "Arriving by SUV around 3pm")
        self.assertTrue(self.reservation.is_flying)
        self.assertEqual(self.reservation.flying_notes, "Flying United, shuttle requested from CPR")

    def test_reservation_flight_model(self):
        flight_arr = ReservationFlight.objects.create(
            reservation=self.reservation,
            flight_type=ReservationFlight.FlightType.ARRIVAL,
            airport="Casper (CPR)",
            flight_number="UA 4521",
            flight_date=date(2026, 7, 5),
            flight_time="14:30:00",
            notes="Need ranch shuttle pickup",
        )
        flight_dep = ReservationFlight.objects.create(
            reservation=self.reservation,
            flight_type=ReservationFlight.FlightType.DEPARTURE,
            airport="Denver (DEN)",
            flight_number="UA 1042",
            flight_date=date(2026, 7, 12),
            flight_time="11:15:00",
            notes="Departing morning flight",
        )

        self.assertEqual(self.reservation.flights.count(), 2)
        self.assertEqual(flight_arr.flight_type, "arrival")
        self.assertEqual(flight_dep.flight_type, "departure")
        self.assertIn("Arrival Flight #UA 4521", str(flight_arr))
        self.assertIn("Departure Flight #UA 1042", str(flight_dep))

    def test_reservation_flight_ordering_arranged_by_airport(self):
        ReservationFlight.objects.create(
            reservation=self.reservation,
            flight_type=ReservationFlight.FlightType.DEPARTURE,
            airport="Denver (DEN)",
            flight_number="UA 200",
            flight_date=date(2026, 7, 12),
            flight_time="16:00:00",
        )
        ReservationFlight.objects.create(
            reservation=self.reservation,
            flight_type=ReservationFlight.FlightType.ARRIVAL,
            airport="Casper (CPR)",
            flight_number="UA 100",
            flight_date=date(2026, 7, 5),
            flight_time="10:00:00",
        )
        ReservationFlight.objects.create(
            reservation=self.reservation,
            flight_type=ReservationFlight.FlightType.ARRIVAL,
            airport="Denver (DEN)",
            flight_number="UA 150",
            flight_date=date(2026, 7, 5),
            flight_time="12:00:00",
        )

        flights = list(self.reservation.flights.all())
        self.assertEqual(flights[0].airport, "Casper (CPR)")
        self.assertEqual(flights[1].airport, "Denver (DEN)")
        self.assertEqual(flights[1].flight_type, "arrival")
        self.assertEqual(flights[2].airport, "Denver (DEN)")
        self.assertEqual(flights[2].flight_type, "departure")

    def test_reservation_create_with_flights_formset(self):
        url = reverse("reservations:reservation_create")
        post_data = {
            "reservation_name": "Flight Test Reservation",
            "reservation_type": Reservation.ReservationType.GUEST_STAY,
            "status": Reservation.ReservationStatus.CONFIRMED,
            "arrival_date": "2026-08-02",
            "departure_date": "2026-08-09",
            "check_in_time": "15:00",
            "check_out_time": "10:00",
            "adult_count": 2,
            "child_count": 0,
            "guest_count": 2,
            "is_flying": True,
            "flights-TOTAL_FORMS": "2",
            "flights-INITIAL_FORMS": "0",
            "flights-MIN_NUM_FORMS": "0",
            "flights-MAX_NUM_FORMS": "1000",
            "flights-0-flight_type": "arrival",
            "flights-0-airport": "Casper (CPR)",
            "flights-0-flight_number": "UA 123",
            "flights-0-flight_date": "2026-08-02",
            "flights-0-flight_time": "14:15",
            "flights-0-notes": "Pick up 2 guests",
            "flights-1-flight_type": "departure",
            "flights-1-airport": "Casper (CPR)",
            "flights-1-flight_number": "UA 456",
            "flights-1-flight_date": "2026-08-09",
            "flights-1-flight_time": "09:45",
            "flights-1-notes": "Drop off at CPR",
        }
        res = self.client.post(url, post_data)
        self.assertEqual(res.status_code, 302)
        created_res = Reservation.objects.get(reservation_name="Flight Test Reservation")
        self.assertEqual(created_res.flights.count(), 2)
        arr_flight = created_res.flights.get(flight_type="arrival")
        self.assertEqual(arr_flight.airport, "Casper (CPR)")
        self.assertEqual(arr_flight.flight_number, "UA 123")

    def test_reservation_form_travel_fields(self):
        form_data = {
            "reservation_name": "Smith Group",
            "reservation_type": Reservation.ReservationType.GUEST_STAY,
            "status": Reservation.ReservationStatus.CONFIRMED,
            "arrival_date": "2026-08-02",
            "departure_date": "2026-08-09",
            "check_in_time": "15:00",
            "check_out_time": "10:00",
            "adult_count": 2,
            "child_count": 1,
            "guest_count": 3,
            "is_driving": True,
            "driving_notes": "Driving from Salt Lake City",
            "is_flying": False,
            "flying_notes": "",
        }
        form = ReservationForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        saved_res = form.save()
        self.assertTrue(saved_res.is_driving)
        self.assertEqual(saved_res.driving_notes, "Driving from Salt Lake City")
        self.assertFalse(saved_res.is_flying)

    def test_reservation_flight_form(self):
        flight_data = {
            "flight_type": "arrival",
            "airport": "Casper (CPR)",
            "flight_number": "UA 500",
            "flight_date": "2026-07-05",
            "flight_time": "13:45",
            "notes": "3 passengers",
        }
        form = ReservationFlightForm(data=flight_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_reservation_detail_view_shows_travel_and_flights(self):
        ReservationFlight.objects.create(
            reservation=self.reservation,
            flight_type=ReservationFlight.FlightType.ARRIVAL,
            airport="Casper (CPR)",
            flight_number="UA 4521",
            flight_date=date(2026, 7, 5),
            flight_time="14:30:00",
        )
        url = reverse("reservations:reservation_detail", args=[self.reservation.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Travel &amp; Flights")
        self.assertContains(response, "Driving")
        self.assertContains(response, "Arriving by SUV around 3pm")
        self.assertContains(response, "Flying")
        self.assertContains(response, "Flying United, shuttle requested from CPR")
        self.assertContains(response, "UA 4521")
        self.assertContains(response, "Casper (CPR)")

    def test_reservation_flight_create_view(self):
        url = reverse("reservations:reservation_flight_create", args=[self.reservation.pk])
        post_data = {
            "flight_type": "arrival",
            "airport": "Denver (DEN)",
            "flight_number": "UA 999",
            "flight_date": "2026-07-05",
            "flight_time": "12:00",
            "notes": "Arriving noon",
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ReservationFlight.objects.filter(
                reservation=self.reservation,
                flight_number="UA 999",
                airport="Denver (DEN)",
            ).exists()
        )

    def test_reservation_flight_update_view(self):
        flight = ReservationFlight.objects.create(
            reservation=self.reservation,
            flight_type=ReservationFlight.FlightType.ARRIVAL,
            airport="Sheridan (SHR)",
            flight_number="UA 100",
            flight_date=date(2026, 7, 5),
            flight_time="15:00:00",
        )
        url = reverse("reservations:reservation_flight_update", args=[flight.pk])
        get_res = self.client.get(url)
        self.assertEqual(get_res.status_code, 200)
        self.assertContains(get_res, "Edit Arrival Flight")

        post_data = {
            "flight_type": "departure",
            "airport": "Billings (BIL)",
            "flight_number": "DL 888",
            "flight_date": "2026-07-12",
            "flight_time": "09:30",
            "notes": "Updated to Billings departure",
        }
        post_res = self.client.post(url, post_data)
        self.assertEqual(post_res.status_code, 302)
        flight.refresh_from_db()
        self.assertEqual(flight.flight_type, "departure")
        self.assertEqual(flight.airport, "Billings (BIL)")
        self.assertEqual(flight.flight_number, "DL 888")

    def test_reservation_flight_delete_view(self):
        flight = ReservationFlight.objects.create(
            reservation=self.reservation,
            flight_type=ReservationFlight.FlightType.ARRIVAL,
            airport="Casper (CPR)",
            flight_number="UA 4521",
        )
        url = reverse("reservations:reservation_flight_delete", args=[flight.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ReservationFlight.objects.filter(pk=flight.pk).exists())

    def test_reservation_flight_auto_date_default_on_create(self):
        url = reverse("reservations:reservation_flight_create", args=[self.reservation.pk])
        # Arrival flight without explicit flight_date should default to reservation.arrival_date
        post_arr = {
            "flight_type": "arrival",
            "airport": "Casper (CPR)",
            "flight_number": "UA 101",
            "flight_date": "",
            "flight_time": "14:00",
        }
        res_arr = self.client.post(url, post_arr)
        self.assertEqual(res_arr.status_code, 302)
        arr_flight = ReservationFlight.objects.get(flight_number="UA 101")
        self.assertEqual(arr_flight.flight_date, self.reservation.arrival_date)

        # Departure flight without explicit flight_date should default to reservation.departure_date
        post_dep = {
            "flight_type": "departure",
            "airport": "Casper (CPR)",
            "flight_number": "UA 102",
            "flight_date": "",
            "flight_time": "10:00",
        }
        res_dep = self.client.post(url, post_dep)
        self.assertEqual(res_dep.status_code, 302)
        dep_flight = ReservationFlight.objects.get(flight_number="UA 102")
        self.assertEqual(dep_flight.flight_date, self.reservation.departure_date)

    def test_reservation_detail_flight_visibility(self):
        # When is_flying is False and no flights exist
        res_no_flying = Reservation.objects.create(
            reservation_name="Non Flying Reservation",
            reservation_type=Reservation.ReservationType.GUEST_STAY,
            status=Reservation.ReservationStatus.CONFIRMED,
            arrival_date=date(2026, 8, 2),
            departure_date=date(2026, 8, 9),
            is_flying=False,
            is_driving=True,
        )
        url = reverse("reservations:reservation_detail", args=[res_no_flying.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Flight information is hidden because Flying is not selected")
        self.assertNotContains(response, "Scheduled Flights (Arranged by Airport)")

        # When is_flying is True
        self.reservation.is_flying = True
        self.reservation.save()
        res_flying = self.client.get(reverse("reservations:reservation_detail", args=[self.reservation.pk]))
        self.assertEqual(res_flying.status_code, 200)
        self.assertContains(res_flying, "Scheduled Flights (Arranged by Airport)")
        self.assertContains(res_flying, "Add Flight")

    def test_reservation_guest_height_and_weight_references_client_profile(self):
        client = Client.objects.create(
            first_name="Jane",
            last_name="Doe",
            height="5'7\"",
            weight="145 lbs",
        )
        guest = ReservationGuest.objects.create(
            reservation=self.reservation,
            client=client,
            age_at_stay=28,
        )

        # Height and weight properties on ReservationGuest reflect the Client profile
        self.assertEqual(guest.height, "5'7\"")
        self.assertEqual(guest.weight, "145 lbs")
        self.assertEqual(guest.effective_height, "5'7\"")
        self.assertEqual(guest.effective_weight, "145 lbs")

        # Updating client profile dynamically updates guest properties without separate stay data
        client.height = "5'8\""
        client.weight = "140 lbs"
        client.save()

        # Re-fetch guest from db
        guest_refreshed = ReservationGuest.objects.select_related("client").get(pk=guest.pk)
        self.assertEqual(guest_refreshed.height, "5'8\"")
        self.assertEqual(guest_refreshed.weight, "140 lbs")

    def test_reservation_guest_form_and_views_without_height_weight(self):
        client = Client.objects.create(
            first_name="Bob",
            last_name="Smith",
            height="6'1\"",
            weight="195 lbs",
        )
        url = reverse("reservations:reservation_guest_create", args=[self.reservation.pk])
        post_data = {
            "client": client.pk,
            "age_at_stay": 35,
            "riding_experience": "intermediate",
            "is_riding": "on",
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        guest = ReservationGuest.objects.get(reservation=self.reservation, client=client)
        self.assertEqual(guest.height, "6'1\"")
        self.assertEqual(guest.weight, "195 lbs")

        # Verify guest update view works cleanly
        update_url = reverse("reservations:reservation_guest_update", args=[guest.pk])
        get_update = self.client.get(update_url)
        self.assertEqual(get_update.status_code, 200)
        self.assertNotContains(get_update, 'name="height"')
        self.assertNotContains(get_update, 'name="weight"')

        # Verify reservation detail displays client's height and weight
        detail_res = self.client.get(reverse("reservations:reservation_detail", args=[self.reservation.pk]))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, "6&#x27;1&quot;")
        self.assertContains(detail_res, "195 lbs")
