from datetime import date, timedelta
from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import site
from apps.cabins.models import Cabin
from apps.clients.models import Client, Household, HouseholdMember, TravelGroup, TravelGroupMember
from apps.reservations.models import OperatingSeason, Reservation, ReservationGuest
from apps.reservations.forms import OperatingSeasonForm
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
