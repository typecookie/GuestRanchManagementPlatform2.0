import calendar
from collections import Counter
from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from apps.groups.decorators import module_permission_required

from apps.reservations.models import OperatingSeason, Reservation, ReservationCabin, ReservationGuest
from apps.reservations.forms import HorseAssignmentForm
from apps.reservations.season_utils import (
    get_next_open_week,
    get_previous_open_week,
    get_open_weeks_sequence,
    get_open_months_sequence,
    get_next_open_month,
    get_previous_open_month,
    is_week_open,
    is_month_open,
    is_date_open,
    get_previous_month_tuple,
    get_next_month_tuple,
    get_current_or_upcoming_season,
    get_categorized_seasons,
    get_default_season,
    get_active_season_for_date,
    get_default_grid_year_month,
)
from apps.horses.models import Horse
from apps.cabins.models import Cabin
from apps.projects.models import Project

def get_current_sunday():
    today = date.today()
    days_since_sunday = (today.weekday() + 1) % 7
    return today - timedelta(days=days_since_sunday)


def resolve_season_and_week(request):
    """
    Resolves season context, week bounds, month bounds, view_mode ('week' vs 'month'),
    and navigation for office views and reports.
    Supports ?season=<id>, ?week=<YYYY-MM-DD>, ?view=month/week, ?month=<1-12>, and ?year=<YYYY>.
    """
    today = date.today()
    categorized_seasons = get_categorized_seasons(today)
    season_param = request.GET.get("season", "").strip()
    week_param = request.GET.get("week", "").strip()
    month_param = request.GET.get("month", "").strip()
    year_param = request.GET.get("year", "").strip()
    view_param = request.GET.get("view", request.GET.get("view_mode", request.GET.get("period", ""))).strip().lower()

    selected_season = None
    if season_param and season_param.isdigit():
        selected_season = OperatingSeason.objects.filter(pk=int(season_param), is_active=True).first()

    if week_param:
        try:
            parsed_date = datetime.strptime(week_param, "%Y-%m-%d").date()
            days_since_sunday = (parsed_date.weekday() + 1) % 7
            week_start = parsed_date - timedelta(days=days_since_sunday)
        except ValueError:
            week_start = get_current_sunday()
    elif selected_season:
        if selected_season.contains_date(today):
            target_date = today
        else:
            target_date = selected_season.start_date
        s_days = (target_date.weekday() + 1) % 7
        target_sunday = target_date - timedelta(days=s_days)
        if is_week_open(target_sunday, target_sunday + timedelta(days=7)):
            week_start = target_sunday
        else:
            week_start = get_next_open_week(target_sunday - timedelta(days=7))
    else:
        days_since_sunday = (today.weekday() + 1) % 7
        today_sunday = today - timedelta(days=days_since_sunday)
        if is_week_open(today_sunday, today_sunday + timedelta(days=7)):
            week_start = today_sunday
        else:
            default_s = categorized_seasons.get("default_season")
            if default_s:
                s_date = default_s.start_date
                s_days = (s_date.weekday() + 1) % 7
                season_sunday = s_date - timedelta(days=s_days)
                if is_week_open(season_sunday, season_sunday + timedelta(days=7)):
                    week_start = season_sunday
                else:
                    week_start = get_next_open_week(season_sunday - timedelta(days=7))
            else:
                week_start = get_next_open_week(today_sunday - timedelta(days=7))

    week_end = week_start + timedelta(days=7)
    previous_week = get_previous_open_week(week_start)
    next_week = get_next_open_week(week_start)

    # Determine view_mode: 'month' or 'week'
    if view_param == "month" or (month_param and not week_param):
        view_mode = "month"
    else:
        view_mode = "week"

    # Determine target year and month
    if year_param.isdigit() and month_param.isdigit():
        target_year = int(year_param)
        target_month = int(month_param)
    elif month_param.isdigit():
        target_month = int(month_param)
        target_year = selected_season.start_date.year if selected_season else (int(year_param) if year_param.isdigit() else (week_start.year if week_param else today.year))
    elif selected_season:
        if selected_season.contains_date(today):
            target_year = today.year
            target_month = today.month
        else:
            target_year = selected_season.start_date.year
            target_month = selected_season.start_date.month
    elif week_param:
        target_year = week_start.year
        target_month = week_start.month
    else:
        def_y, def_m = get_default_grid_year_month(today)
        target_year = def_y
        target_month = def_m

    if target_month < 1 or target_month > 12:
        target_month = 6

    last_day_of_month = calendar.monthrange(target_year, target_month)[1]
    month_start = date(target_year, target_month, 1)
    month_end = date(target_year, target_month, last_day_of_month) + timedelta(days=1)
    month_end_display = date(target_year, target_month, last_day_of_month)

    previous_month_year, previous_month_month = get_previous_open_month(target_year, target_month)
    next_month_year, next_month_month = get_next_open_month(target_year, target_month)
    previous_month_start = date(previous_month_year, previous_month_month, 1)
    next_month_start = date(next_month_year, next_month_month, 1)

    current_season = (
        selected_season
        or (get_active_season_for_date(month_start) if view_mode == "month" else None)
        or get_active_season_for_date(week_start)
        or get_active_season_for_date(week_end - timedelta(days=1))
        or categorized_seasons.get("default_season")
    )

    is_open = is_week_open(week_start, week_end)
    is_month_open_flag = is_month_open(target_year, target_month)

    # Sequence of open months for carousel tabs and navigation
    month_seq_start = month_start if view_mode == "month" else (selected_season.start_date if selected_season else (week_start if is_date_open(week_start) else None))
    open_months = get_open_months_sequence(start_date=month_seq_start, num_months=4, season=selected_season)

    period_start = month_start if view_mode == "month" else week_start
    period_end = month_end if view_mode == "month" else week_end

    return {
        "today": today,
        "view_mode": view_mode,
        "week_start": week_start,
        "week_end": week_end,
        "month_start": month_start,
        "month_end": month_end,
        "month_end_display": month_end_display,
        "target_year": target_year,
        "target_month": target_month,
        "period_start": period_start,
        "period_end": period_end,
        "previous_week": previous_week,
        "next_week": next_week,
        "previous_month_year": previous_month_year,
        "previous_month_month": previous_month_month,
        "next_month_year": next_month_year,
        "next_month_month": next_month_month,
        "previous_month_start": previous_month_start,
        "next_month_start": next_month_start,
        "categorized_seasons": categorized_seasons,
        "current_season": current_season,
        "is_week_open": is_open,
        "is_month_open": is_month_open_flag,
        "selected_season": selected_season,
        "open_months": open_months,
    }


def parse_week_start(request):
    return resolve_season_and_week(request)["week_start"]


@module_permission_required('Ranch', 'read')
def ranch_operations(request):
    projects = Project.objects.filter(show_in_ranch_operations=True)
    context = {
        'projects': projects,
    }
    return render(request, "ranch/ranch_operations.html", context)


def build_weekly_horse_saddle_task(week_start, num_weeks=4):
    """
    Builds week-by-week horse, saddle, and rider readiness data
    for current and upcoming open weeks.
    """
    weeks_data = []
    open_weeks = get_open_weeks_sequence(week_start, num_weeks=num_weeks)

    for w_idx, w_start in enumerate(open_weeks):
        w_end = w_start + timedelta(days=7)

        reservations = Reservation.objects.select_related(
            "primary_contact", "household", "travel_group"
        ).filter(
            arrival_date__lt=w_end,
            departure_date__gt=w_start,
        ).exclude(
            status=Reservation.ReservationStatus.CANCELLED,
        ).order_by("arrival_date", "reservation_name")

        res_ids = reservations.values_list("id", flat=True)

        guests = ReservationGuest.objects.select_related(
            "reservation", "client", "cabin", "horse", "saddle"
        ).filter(
            reservation_id__in=res_ids
        ).order_by("cabin__capacity", "cabin__sort_order", "cabin__name", "client__last_name", "client__first_name")

        res_guest_map = {r.id: [] for r in reservations}

        horses_assigned = 0
        saddles_assigned = 0
        missing_info_count = 0
        total_riders = 0

        for g in guests:
            is_rider = g.is_riding and g.riding_experience != ReservationGuest.RidingExperience.NON_RIDER
            g.is_rider = is_rider

            effective_h = g.client.height if g.client else ""
            effective_w = g.client.weight if g.client else ""
            effective_exp = g.riding_experience

            missing_fields = []
            if is_rider:
                total_riders += 1
                if not effective_h or not str(effective_h).strip():
                    missing_fields.append("Height")
                if not effective_w or not str(effective_w).strip():
                    missing_fields.append("Weight")
                if not effective_exp or effective_exp == ReservationGuest.RidingExperience.UNKNOWN:
                    missing_fields.append("Experience")
                if g.age_at_stay is None and not (g.client and g.client.date_of_birth):
                    missing_fields.append("Age")

                if g.horse_id:
                    horses_assigned += 1
                if g.saddle_id:
                    saddles_assigned += 1
                if missing_fields:
                    missing_info_count += 1

            g.missing_rider_fields = missing_fields
            g.needs_horse = is_rider and not g.horse_id
            g.needs_saddle = is_rider and not g.saddle_id

            if g.reservation_id in res_guest_map:
                res_guest_map[g.reservation_id].append(g)

        missing_horses = total_riders - horses_assigned
        missing_saddles = total_riders - saddles_assigned

        reservation_items = []
        for r in reservations:
            r_guests = res_guest_map.get(r.id, [])
            r_riders = [g for g in r_guests if g.is_rider]
            r_needs_horses = [g for g in r_riders if g.needs_horse]
            r_needs_saddles = [g for g in r_riders if g.needs_saddle]
            r_missing_info = [g for g in r_riders if g.missing_rider_fields]

            reservation_items.append({
                "reservation": r,
                "guests": r_guests,
                "riders": r_riders,
                "riders_count": len(r_riders),
                "needs_horses_count": len(r_needs_horses),
                "needs_saddles_count": len(r_needs_saddles),
                "missing_info_count": len(r_missing_info),
                "is_ready": (len(r_riders) == 0) or (len(r_needs_horses) == 0 and len(r_needs_saddles) == 0 and len(r_missing_info) == 0),
            })

        weeks_data.append({
            "week_start": w_start,
            "week_end": w_end,
            "is_first_week": w_idx == 0,
            "total_reservations": reservations.count(),
            "total_guests": len(guests),
            "total_riders": total_riders,
            "horses_assigned": horses_assigned,
            "saddles_assigned": saddles_assigned,
            "missing_horses": missing_horses,
            "missing_saddles": missing_saddles,
            "missing_info_count": missing_info_count,
            "is_all_complete": total_riders > 0 and missing_horses == 0 and missing_saddles == 0 and missing_info_count == 0,
            "reservations": reservation_items,
            "has_records": len(guests) > 0,
        })

    return weeks_data


def build_weekly_intake_task(week_start, num_weeks=4):
    """
    Builds week-by-week intake task data (release forms, deposits, missing info)
    for current and upcoming open weeks.
    """
    weeks_data = []
    open_weeks = get_open_weeks_sequence(week_start, num_weeks=num_weeks)

    for w_idx, w_start in enumerate(open_weeks):
        w_end = w_start + timedelta(days=7)

        reservations = Reservation.objects.select_related(
            "primary_contact", "household", "travel_group"
        ).filter(
            arrival_date__lt=w_end,
            departure_date__gt=w_start,
        ).exclude(
            status=Reservation.ReservationStatus.CANCELLED,
        ).order_by("arrival_date", "reservation_name")

        res_ids = reservations.values_list("id", flat=True)

        guests = ReservationGuest.objects.select_related(
            "reservation", "client", "cabin"
        ).filter(
            reservation_id__in=res_ids
        ).order_by("cabin__capacity", "cabin__sort_order", "cabin__name", "client__last_name", "client__first_name")

        res_guest_map = {r.id: [] for r in reservations}
        for g in guests:
            if g.reservation_id in res_guest_map:
                res_guest_map[g.reservation_id].append(g)

        deposits_received = 0
        deposits_requested = 0
        deposits_needed = 0

        total_signed_releases = 0
        total_unsigned_releases = 0

        reservation_items = []

        for r in reservations:
            r_guests = res_guest_map.get(r.id, [])
            total_r_guests = len(r_guests)

            signed_guests = [g for g in r_guests if g.signed_release]
            unsigned_guests = [g for g in r_guests if not g.signed_release]

            total_signed_releases += len(signed_guests)
            total_unsigned_releases += len(unsigned_guests)

            if r.deposit_received:
                deposits_received += 1
                deposit_status = "received"
                deposit_badge = "badge-success"
                deposit_label = "Deposit Received"
            elif r.deposit_request_sent:
                deposits_requested += 1
                deposit_status = "sent"
                deposit_badge = "badge-warning"
                deposit_label = "Request Sent"
            else:
                deposits_needed += 1
                deposit_status = "needed"
                deposit_badge = "badge-danger"
                deposit_label = "Deposit Needed"

            missing_items = []
            if not r.deposit_received:
                if not r.deposit_request_sent:
                    missing_items.append("Deposit Not Requested")
                else:
                    missing_items.append("Deposit Pending")

            if unsigned_guests:
                missing_items.append(f"{len(unsigned_guests)} Unsigned Release{'s' if len(unsigned_guests) > 1 else ''}")

            unassigned_cabins = [g for g in r_guests if not g.cabin_id]
            if unassigned_cabins:
                missing_items.append(f"{len(unassigned_cabins)} Unassigned Cabin{'s' if len(unassigned_cabins) > 1 else ''}")

            primary = r.primary_contact
            if not primary:
                missing_items.append("No Primary Contact")
            else:
                if not primary.phone and not primary.email:
                    missing_items.append("Missing Contact Info")

            is_complete = (len(missing_items) == 0 and r.deposit_received and len(unsigned_guests) == 0)

            reservation_items.append({
                "reservation": r,
                "guests": r_guests,
                "total_guests": total_r_guests,
                "signed_count": len(signed_guests),
                "unsigned_count": len(unsigned_guests),
                "unsigned_guests": unsigned_guests,
                "deposit_status": deposit_status,
                "deposit_badge": deposit_badge,
                "deposit_label": deposit_label,
                "missing_items": missing_items,
                "is_complete": is_complete,
            })

        weeks_data.append({
            "week_start": w_start,
            "week_end": w_end,
            "is_first_week": w_idx == 0,
            "total_reservations": reservations.count(),
            "total_guests": len(guests),
            "deposits_received": deposits_received,
            "deposits_requested": deposits_requested,
            "deposits_needed": deposits_needed,
            "total_signed_releases": total_signed_releases,
            "total_unsigned_releases": total_unsigned_releases,
            "is_all_complete": len(reservations) > 0 and deposits_needed == 0 and total_unsigned_releases == 0 and all(item["is_complete"] for item in reservation_items),
            "reservations": reservation_items,
            "has_records": len(reservations) > 0,
        })

    return weeks_data


def build_monthly_horse_saddle_task(target_date=None, num_months=4, season=None):
    """
    Builds month-by-month horse, saddle, and rider readiness data
    for current and upcoming open months.
    """
    months_data = []
    open_months = get_open_months_sequence(target_date, num_months=num_months, season=season)

    for m_idx, m_item in enumerate(open_months):
        m_start = m_item["start_date"]
        m_end = m_item["end_date"] + timedelta(days=1)

        reservations = Reservation.objects.select_related(
            "primary_contact", "household", "travel_group"
        ).filter(
            arrival_date__lt=m_end,
            departure_date__gt=m_start,
        ).exclude(
            status=Reservation.ReservationStatus.CANCELLED,
        ).order_by("arrival_date", "reservation_name")

        res_ids = reservations.values_list("id", flat=True)

        guests = ReservationGuest.objects.select_related(
            "reservation", "client", "cabin", "horse", "saddle"
        ).filter(
            reservation_id__in=res_ids
        ).order_by("cabin__capacity", "cabin__sort_order", "cabin__name", "client__last_name", "client__first_name")

        res_guest_map = {r.id: [] for r in reservations}

        horses_assigned = 0
        saddles_assigned = 0
        missing_info_count = 0
        total_riders = 0

        for g in guests:
            is_rider = g.is_riding and g.riding_experience != ReservationGuest.RidingExperience.NON_RIDER
            g.is_rider = is_rider

            effective_h = g.client.height if g.client else ""
            effective_w = g.client.weight if g.client else ""
            effective_exp = g.riding_experience

            missing_fields = []
            if is_rider:
                total_riders += 1
                if not effective_h or not str(effective_h).strip():
                    missing_fields.append("Height")
                if not effective_w or not str(effective_w).strip():
                    missing_fields.append("Weight")
                if not effective_exp or effective_exp == ReservationGuest.RidingExperience.UNKNOWN:
                    missing_fields.append("Experience")
                if g.age_at_stay is None and not (g.client and g.client.date_of_birth):
                    missing_fields.append("Age")

                if g.horse_id:
                    horses_assigned += 1
                if g.saddle_id:
                    saddles_assigned += 1
                if missing_fields:
                    missing_info_count += 1

            g.missing_rider_fields = missing_fields
            g.needs_horse = is_rider and not g.horse_id
            g.needs_saddle = is_rider and not g.saddle_id

            if g.reservation_id in res_guest_map:
                res_guest_map[g.reservation_id].append(g)

        missing_horses = total_riders - horses_assigned
        missing_saddles = total_riders - saddles_assigned

        reservation_items = []
        for r in reservations:
            r_guests = res_guest_map.get(r.id, [])
            r_riders = [g for g in r_guests if g.is_rider]
            r_needs_horses = [g for g in r_riders if g.needs_horse]
            r_needs_saddles = [g for g in r_riders if g.needs_saddle]
            r_missing_info = [g for g in r_riders if g.missing_rider_fields]

            reservation_items.append({
                "reservation": r,
                "guests": r_guests,
                "riders": r_riders,
                "riders_count": len(r_riders),
                "needs_horses_count": len(r_needs_horses),
                "needs_saddles_count": len(r_needs_saddles),
                "missing_info_count": len(r_missing_info),
                "is_ready": (len(r_riders) == 0) or (len(r_needs_horses) == 0 and len(r_needs_saddles) == 0 and len(r_missing_info) == 0),
            })

        months_data.append({
            "month_idx": m_idx,
            "is_first_month": m_idx == 0,
            "month_info": m_item,
            "month_label": m_item["label"],
            "month_short": m_item["short_label"],
            "month_name": m_item["month_name"],
            "year": m_item["year"],
            "month": m_item["month"],
            "month_start": m_start,
            "month_end": m_item["end_date"],
            "total_reservations": reservations.count(),
            "total_guests": len(guests),
            "total_riders": total_riders,
            "horses_assigned": horses_assigned,
            "saddles_assigned": saddles_assigned,
            "missing_horses": missing_horses,
            "missing_saddles": missing_saddles,
            "missing_info_count": missing_info_count,
            "is_all_complete": total_riders > 0 and missing_horses == 0 and missing_saddles == 0 and missing_info_count == 0,
            "reservations": reservation_items,
            "has_records": len(guests) > 0,
        })

    return months_data


def build_monthly_intake_task(target_date=None, num_months=4, season=None):
    """
    Builds month-by-month intake task data (release forms, deposits, missing info)
    for current and upcoming open months.
    """
    months_data = []
    open_months = get_open_months_sequence(target_date, num_months=num_months, season=season)

    for m_idx, m_item in enumerate(open_months):
        m_start = m_item["start_date"]
        m_end = m_item["end_date"] + timedelta(days=1)

        reservations = Reservation.objects.select_related(
            "primary_contact", "household", "travel_group"
        ).filter(
            arrival_date__lt=m_end,
            departure_date__gt=m_start,
        ).exclude(
            status=Reservation.ReservationStatus.CANCELLED,
        ).order_by("arrival_date", "reservation_name")

        res_ids = reservations.values_list("id", flat=True)

        guests = ReservationGuest.objects.select_related(
            "reservation", "client", "cabin"
        ).filter(
            reservation_id__in=res_ids
        ).order_by("cabin__capacity", "cabin__sort_order", "cabin__name", "client__last_name", "client__first_name")

        res_guest_map = {r.id: [] for r in reservations}
        for g in guests:
            if g.reservation_id in res_guest_map:
                res_guest_map[g.reservation_id].append(g)

        deposits_received = 0
        deposits_requested = 0
        deposits_needed = 0

        total_signed_releases = 0
        total_unsigned_releases = 0

        reservation_items = []

        for r in reservations:
            r_guests = res_guest_map.get(r.id, [])
            total_r_guests = len(r_guests)

            signed_guests = [g for g in r_guests if g.signed_release]
            unsigned_guests = [g for g in r_guests if not g.signed_release]

            total_signed_releases += len(signed_guests)
            total_unsigned_releases += len(unsigned_guests)

            if r.deposit_received:
                deposits_received += 1
                deposit_status = "received"
                deposit_badge = "badge-success"
                deposit_label = "Deposit Received"
            elif r.deposit_request_sent:
                deposits_requested += 1
                deposit_status = "sent"
                deposit_badge = "badge-warning"
                deposit_label = "Request Sent"
            else:
                deposits_needed += 1
                deposit_status = "needed"
                deposit_badge = "badge-danger"
                deposit_label = "Deposit Needed"

            missing_items = []
            if not r.deposit_received:
                if not r.deposit_request_sent:
                    missing_items.append("Deposit Not Requested")
                else:
                    missing_items.append("Deposit Pending")

            if unsigned_guests:
                missing_items.append(f"{len(unsigned_guests)} Unsigned Release{'s' if len(unsigned_guests) > 1 else ''}")

            unassigned_cabins = [g for g in r_guests if not g.cabin_id]
            if unassigned_cabins:
                missing_items.append(f"{len(unassigned_cabins)} Unassigned Cabin{'s' if len(unassigned_cabins) > 1 else ''}")

            primary = r.primary_contact
            if not primary:
                missing_items.append("No Primary Contact")
            else:
                if not primary.phone and not primary.email:
                    missing_items.append("Missing Contact Info")

            is_complete = (len(missing_items) == 0 and r.deposit_received and len(unsigned_guests) == 0)

            reservation_items.append({
                "reservation": r,
                "guests": r_guests,
                "total_guests": total_r_guests,
                "signed_count": len(signed_guests),
                "unsigned_count": len(unsigned_guests),
                "unsigned_guests": unsigned_guests,
                "deposit_status": deposit_status,
                "deposit_badge": deposit_badge,
                "deposit_label": deposit_label,
                "missing_items": missing_items,
                "is_complete": is_complete,
            })

        months_data.append({
            "month_idx": m_idx,
            "is_first_month": m_idx == 0,
            "month_info": m_item,
            "month_label": m_item["label"],
            "month_short": m_item["short_label"],
            "month_name": m_item["month_name"],
            "year": m_item["year"],
            "month": m_item["month"],
            "month_start": m_start,
            "month_end": m_item["end_date"],
            "total_reservations": reservations.count(),
            "total_guests": len(guests),
            "deposits_received": deposits_received,
            "deposits_requested": deposits_requested,
            "deposits_needed": deposits_needed,
            "total_signed_releases": total_signed_releases,
            "total_unsigned_releases": total_unsigned_releases,
            "is_all_complete": len(reservations) > 0 and deposits_needed == 0 and total_unsigned_releases == 0 and all(item["is_complete"] for item in reservation_items),
            "reservations": reservation_items,
            "has_records": len(reservations) > 0,
        })

    return months_data


def build_booking_alerts(period_start, period_end=None):
    """
    Detects operational oddities and booking anomalies for the given time period (week or month):
    - Multiple individuals / parties in a cabin without a TravelGroup
    - Multi-guest reservations without a Household or TravelGroup
    - Multiple active reservations overlapping in the same cabin
    - Cabin capacity overages
    - Multi-household reservations without a TravelGroup
    - Reservation guest count mismatches
    - Active reservations with zero guests attached
    - Cabin assignments outside reservation stay dates
    """
    if period_end is None:
        period_end = period_start + timedelta(days=7)
    alerts = []

    reservations = Reservation.objects.select_related(
        "primary_contact", "household", "travel_group"
    ).prefetch_related(
        "guests__client__household_memberships__household",
        "guests__client__travel_group_memberships__travel_group",
        "guests__cabin",
        "cabin_assignments__cabin",
    ).filter(
        arrival_date__lt=period_end,
        departure_date__gt=period_start,
    ).exclude(
        status=Reservation.ReservationStatus.CANCELLED,
    ).order_by("arrival_date", "reservation_name")

    res_list = list(reservations)

    cabin_guests_map = {}
    cabin_reservations_map = {}

    for res in res_list:
        guests = list(res.guests.all())
        guest_count = len(guests)

        # 1. Multi-guest reservation without household or travel group
        if guest_count > 1 or res.guest_count > 1:
            if not res.household_id and not res.travel_group_id:
                guest_names = ", ".join(g.client.full_name for g in guests) if guests else "No guests added yet"
                client_ids_param = ",".join(str(g.client_id) for g in guests if g.client_id)
                alerts.append({
                    "id": f"res_no_group_{res.id}",
                    "category": "Missing Group",
                    "severity": "warning",
                    "badge_class": "badge-warning",
                    "title": f"Multi-Guest Reservation Missing Household/Group: {res.reservation_name}",
                    "description": f"Reservation '{res.reservation_name}' has {guest_count or res.guest_count} guests ({guest_names}) but is not linked to a Household or Travel Group.",
                    "reservation": res,
                    "quick_actions": [
                        {"label": "Create Both (Group Builder)", "url": f"/clients/group-builder/?mode=both&reservation_id={res.id}&clients={client_ids_param}&name={res.reservation_name}", "btn_class": "button-primary"},
                        {"label": "Create Household", "url": f"/clients/group-builder/?mode=household&reservation_id={res.id}&clients={client_ids_param}&name={res.reservation_name}", "btn_class": "button-secondary"},
                        {"label": "Create Travel Group", "url": f"/clients/group-builder/?mode=travel_group&reservation_id={res.id}&clients={client_ids_param}&name={res.reservation_name}", "btn_class": "button-secondary"},
                        {"label": "Edit Reservation", "url": f"/reservations/{res.id}/edit/", "btn_class": "button-secondary"},
                    ]
                })

        # 2. Multi-household guests in single reservation without travel group
        if guest_count > 1 and not res.travel_group_id:
            household_names = set()
            for g in guests:
                client_hh = g.client.household_memberships.all()
                if client_hh:
                    for hm in client_hh:
                        household_names.add(hm.household.name)
                elif res.household_id:
                    household_names.add(res.household.name)
            if len(household_names) > 1:
                client_ids_param = ",".join(str(g.client_id) for g in guests if g.client_id)
                alerts.append({
                    "id": f"res_multi_hh_{res.id}",
                    "category": "Multi-Household Party",
                    "severity": "warning",
                    "badge_class": "badge-warning",
                    "title": f"Multi-Household Reservation Needs Travel Group: {res.reservation_name}",
                    "description": f"Guests on '{res.reservation_name}' belong to multiple distinct households ({', '.join(sorted(household_names))}) but are not organized into a Travel Group.",
                    "reservation": res,
                    "quick_actions": [
                        {"label": "Create Both (Group Builder)", "url": f"/clients/group-builder/?mode=both&reservation_id={res.id}&clients={client_ids_param}&name={res.reservation_name}", "btn_class": "button-primary"},
                        {"label": "Create Travel Group", "url": f"/clients/group-builder/?mode=travel_group&reservation_id={res.id}&clients={client_ids_param}&name={res.reservation_name}", "btn_class": "button-secondary"},
                        {"label": "Create Household", "url": f"/clients/group-builder/?mode=household&reservation_id={res.id}&clients={client_ids_param}&name={res.reservation_name}", "btn_class": "button-secondary"},
                        {"label": "Edit Reservation", "url": f"/reservations/{res.id}/edit/", "btn_class": "button-secondary"},
                    ]
                })

        # 3. Active reservation with zero guests
        if guest_count == 0:
            alerts.append({
                "id": f"res_zero_guests_{res.id}",
                "category": "Zero Guests",
                "severity": "warning",
                "badge_class": "badge-warning",
                "title": f"Reservation Has No Guests Attached: {res.reservation_name}",
                "description": f"Reservation '{res.reservation_name}' ({res.arrival_date.strftime('%b %d')} – {res.departure_date.strftime('%b %d, %Y')}) is active but has zero guest profiles added.",
                "reservation": res,
                "quick_actions": [
                    {"label": "Add Guest", "url": f"/reservations/{res.id}/guests/new/", "btn_class": "button-primary"},
                    {"label": "View Reservation", "url": f"/reservations/{res.id}/", "btn_class": "button-secondary"},
                ]
            })

        # 4. Guest count mismatch
        if res.guest_count > 0 and guest_count != res.guest_count and guest_count > 0:
            alerts.append({
                "id": f"res_count_mismatch_{res.id}",
                "category": "Count Mismatch",
                "severity": "info",
                "badge_class": "badge-info",
                "title": f"Guest Count Mismatch: {res.reservation_name}",
                "description": f"Reservation header states {res.guest_count} guests, but {guest_count} guest records are attached.",
                "reservation": res,
                "quick_actions": [
                    {"label": "Manage Guests", "url": f"/reservations/{res.id}/", "btn_class": "button-secondary"},
                    {"label": "Edit Reservation", "url": f"/reservations/{res.id}/edit/", "btn_class": "button-secondary"},
                ]
            })

        # Track cabin assignments for cabin-level anomalies
        for g in guests:
            if g.cabin:
                cabin_guests_map.setdefault(g.cabin, []).append((g, res))
                cabin_reservations_map.setdefault(g.cabin, set()).add(res)

        for ca in res.cabin_assignments.all():
            if ca.arrival_date < period_end and ca.departure_date > period_start:
                cabin_reservations_map.setdefault(ca.cabin, set()).add(res)

                # Check cabin assignment date bounds
                if ca.arrival_date < res.arrival_date or ca.departure_date > res.departure_date:
                    alerts.append({
                        "id": f"ca_date_mismatch_{ca.id}",
                        "category": "Date Mismatch",
                        "severity": "warning",
                        "badge_class": "badge-warning",
                        "title": f"Cabin Dates Outside Reservation: {ca.cabin.name}",
                        "description": f"Cabin assignment for {ca.cabin.name} ({ca.arrival_date.strftime('%b %d')} – {ca.departure_date.strftime('%b %d, %Y')}) falls outside reservation dates ({res.arrival_date.strftime('%b %d')} – {res.departure_date.strftime('%b %d, %Y')}).",
                        "reservation": res,
                        "quick_actions": [
                            {"label": "Manage Cabin Assignments", "url": f"/reservations/{res.id}/", "btn_class": "button-primary"},
                        ]
                    })

    # Cabin level checks
    all_occupied_cabins = set(cabin_guests_map.keys()) | set(cabin_reservations_map.keys())

    for cabin in sorted(all_occupied_cabins, key=lambda c: (c.capacity, c.sort_order, c.name)):
        c_guests_pairs = cabin_guests_map.get(cabin, [])
        c_reservations = list(cabin_reservations_map.get(cabin, []))
        total_cabin_guests = len(c_guests_pairs)

        # 5. Cabin over-capacity
        if cabin.capacity and total_cabin_guests > cabin.capacity:
            guest_names_str = ", ".join(g.client.full_name for g, _ in c_guests_pairs)
            cabin_client_ids = ",".join(str(g.client_id) for g, _ in c_guests_pairs if g.client_id)
            alerts.append({
                "id": f"cabin_capacity_{cabin.id}",
                "category": "Capacity Exceeded",
                "severity": "danger",
                "badge_class": "badge-danger",
                "title": f"Cabin Over Capacity: {cabin.name}",
                "description": f"{total_cabin_guests} guests ({guest_names_str}) are assigned to {cabin.name}, exceeding its maximum capacity of {cabin.capacity}.",
                "cabin": cabin,
                "reservations": c_reservations,
                "quick_actions": [
                    {"label": "Create Both (Group Builder)", "url": f"/clients/group-builder/?mode=both&cabin_id={cabin.id}&clients={cabin_client_ids}&name={cabin.name}", "btn_class": "button-primary"},
                    {"label": "Create Travel Group", "url": f"/clients/group-builder/?mode=travel_group&cabin_id={cabin.id}&clients={cabin_client_ids}&name={cabin.name}", "btn_class": "button-secondary"},
                    {"label": f"View {cabin.name}", "url": f"/cabins/{cabin.id}/", "btn_class": "button-secondary"},
                ]
            })

        # 6. Multiple reservations assigned to same cabin
        if len(c_reservations) > 1:
            res_tg_ids = {r.travel_group_id for r in c_reservations if r.travel_group_id}
            res_hh_ids = {r.household_id for r in c_reservations if r.household_id}
            is_grouped = (len(res_tg_ids) == 1 and all(r.travel_group_id for r in c_reservations)) or \
                         (len(res_hh_ids) == 1 and all(r.household_id for r in c_reservations))

            if not is_grouped:
                res_names_str = " and ".join(f"'{r.reservation_name}'" for r in c_reservations)
                cabin_client_ids = ",".join(str(g.client_id) for g, _ in c_guests_pairs if g.client_id)
                alerts.append({
                    "id": f"cabin_multi_res_{cabin.id}",
                    "category": "Cabin Overlap",
                    "severity": "warning",
                    "badge_class": "badge-warning",
                    "title": f"Multiple Reservations Sharing Cabin: {cabin.name}",
                    "description": f"{len(c_reservations)} distinct unlinked reservations ({res_names_str}) are assigned to {cabin.name} in the period of {period_start.strftime('%b %d, %Y')}.",
                    "cabin": cabin,
                    "reservations": c_reservations,
                    "quick_actions": [
                        {"label": "Create Both (Group Builder)", "url": f"/clients/group-builder/?mode=both&cabin_id={cabin.id}&clients={cabin_client_ids}&name={cabin.name}", "btn_class": "button-primary"},
                        {"label": "Create Travel Group", "url": f"/clients/group-builder/?mode=travel_group&cabin_id={cabin.id}&clients={cabin_client_ids}&name={cabin.name}", "btn_class": "button-secondary"},
                        {"label": "Create Household", "url": f"/clients/group-builder/?mode=household&cabin_id={cabin.id}&clients={cabin_client_ids}&name={cabin.name}", "btn_class": "button-secondary"},
                        {"label": f"View {cabin.name}", "url": f"/cabins/{cabin.id}/", "btn_class": "button-secondary"},
                    ]
                })

        # 7. Multiple individuals / parties in a cabin not organized in a travel group
        if total_cabin_guests > 1 or len(c_reservations) > 1:
            travel_group_ids = set()
            household_ids = set()
            parties = []

            for g, r in c_guests_pairs:
                client = g.client
                tg_id = r.travel_group_id
                hh_id = r.household_id

                for tg_mem in client.travel_group_memberships.all():
                    if tg_mem.travel_group_id:
                        travel_group_ids.add(tg_mem.travel_group_id)
                for hh_mem in client.household_memberships.all():
                    if hh_mem.household_id:
                        household_ids.add(hh_mem.household_id)

                if tg_id:
                    travel_group_ids.add(tg_id)
                if hh_id:
                    household_ids.add(hh_id)
                parties.append(client.full_name)

            is_ungrouped = False
            if len(c_reservations) > 1:
                res_tg_ids = {r.travel_group_id for r in c_reservations if r.travel_group_id}
                res_hh_ids = {r.household_id for r in c_reservations if r.household_id}
                if not ((len(res_tg_ids) == 1 and all(r.travel_group_id for r in c_reservations)) or
                        (len(res_hh_ids) == 1 and all(r.household_id for r in c_reservations))):
                    is_ungrouped = True
            elif len(household_ids) > 1 or (len(c_guests_pairs) > 1 and len(household_ids) == 0 and len(travel_group_ids) == 0):
                if len(travel_group_ids) == 0:
                    is_ungrouped = True

            if is_ungrouped:
                party_list_str = ", ".join(parties) if parties else "multiple guests"
                cabin_client_ids = ",".join(str(g.client_id) for g, _ in c_guests_pairs if g.client_id)
                alerts.append({
                    "id": f"cabin_ungrouped_{cabin.id}",
                    "category": "Ungrouped Cabin Sharing",
                    "severity": "warning",
                    "badge_class": "badge-warning",
                    "title": f"Cabin Shared Without Travel Group: {cabin.name}",
                    "description": f"{cabin.name} has multiple individuals/parties staying together ({party_list_str}) who are not organized into a shared Travel Group or Family Group.",
                    "cabin": cabin,
                    "reservations": c_reservations,
                    "quick_actions": [
                        {"label": "Create Both (Group Builder)", "url": f"/clients/group-builder/?mode=both&cabin_id={cabin.id}&clients={cabin_client_ids}&name={cabin.name}", "btn_class": "button-primary"},
                        {"label": "Create Travel Group", "url": f"/clients/group-builder/?mode=travel_group&cabin_id={cabin.id}&clients={cabin_client_ids}&name={cabin.name}", "btn_class": "button-secondary"},
                        {"label": "Create Household", "url": f"/clients/group-builder/?mode=household&cabin_id={cabin.id}&clients={cabin_client_ids}&name={cabin.name}", "btn_class": "button-secondary"},
                        {"label": f"View {cabin.name}", "url": f"/cabins/{cabin.id}/", "btn_class": "button-secondary"},
                    ]
                })

    return alerts


@module_permission_required('Ranch', 'read')
def office_dashboard(request):
    season_info = resolve_season_and_week(request)
    view_mode = season_info["view_mode"]
    week_start = season_info["week_start"]
    week_end = season_info["week_end"]
    month_start = season_info["month_start"]
    month_end = season_info["month_end"]
    month_end_display = season_info["month_end_display"]
    period_start = season_info["period_start"]
    period_end = season_info["period_end"]
    previous_week = season_info["previous_week"]
    next_week = season_info["next_week"]
    previous_month_year = season_info["previous_month_year"]
    previous_month_month = season_info["previous_month_month"]
    next_month_year = season_info["next_month_year"]
    next_month_month = season_info["next_month_month"]
    previous_month_start = season_info["previous_month_start"]
    next_month_start = season_info["next_month_start"]
    current_season = season_info["current_season"]
    categorized_seasons = season_info["categorized_seasons"]
    is_week_open_flag = season_info["is_week_open"]
    is_month_open_flag = season_info["is_month_open"]
    today = season_info["today"]
    open_months = season_info["open_months"]

    reservations_period = Reservation.objects.select_related(
        "primary_contact",
        "household",
        "travel_group",
    ).filter(
        arrival_date__lt=period_end,
        departure_date__gt=period_start,
    ).exclude(
        status=Reservation.ReservationStatus.CANCELLED,
    ).order_by(
        "arrival_date",
        "reservation_name",
    )

    reservation_ids = reservations_period.values_list("id", flat=True)

    unassigned_guest_reservations = reservations_period.annotate(
        unassigned_guest_count=Count(
            "guests",
            filter=Q(guests__cabin__isnull=True),
        )
    ).filter(
        unassigned_guest_count__gt=0,
    )

    reservation_guests_period = ReservationGuest.objects.select_related(
        "reservation",
        "client",
        "cabin",
    ).filter(
        reservation_id__in=reservation_ids,
    )

    cabin_assignments_period = ReservationCabin.objects.select_related(
        "reservation",
        "cabin",
    ).filter(
        reservation_id__in=reservation_ids,
        arrival_date__lt=period_end,
        departure_date__gt=period_start,
    ).order_by(
        "cabin__capacity",
        "cabin__sort_order",
        "cabin__name",
    )

    horse_saddle_weeks = build_weekly_horse_saddle_task(week_start, num_weeks=4)
    horse_saddle_months = build_monthly_horse_saddle_task(month_start, num_months=4, season=current_season)

    intake_weeks = build_weekly_intake_task(week_start, num_weeks=4)
    intake_months = build_monthly_intake_task(month_start, num_months=4, season=current_season)

    booking_alerts = build_booking_alerts(period_start, period_end)

    context = {
        "today": today,
        "view_mode": view_mode,
        "week_start": week_start,
        "week_end": week_end,
        "month_start": month_start,
        "month_end": month_end,
        "month_end_display": month_end_display,
        "target_year": season_info["target_year"],
        "target_month": season_info["target_month"],
        "period_start": period_start,
        "period_end": period_end,
        "previous_week": previous_week,
        "next_week": next_week,
        "previous_month_year": previous_month_year,
        "previous_month_month": previous_month_month,
        "next_month_year": next_month_year,
        "next_month_month": next_month_month,
        "previous_month_start": previous_month_start,
        "next_month_start": next_month_start,
        "current_season": current_season,
        "categorized_seasons": categorized_seasons,
        "is_week_open": is_week_open_flag,
        "is_month_open": is_month_open_flag,
        "reservations_this_week": reservations_period,
        "reservations_period": reservations_period,
        "unassigned_guest_reservations": unassigned_guest_reservations,
        "reservation_count": reservations_period.count(),
        "guest_count": reservation_guests_period.count(),
        "unassigned_guest_count": reservation_guests_period.filter(cabin__isnull=True).count(),
        "occupied_cabin_count": cabin_assignments_period.values("cabin").distinct().count(),
        "horse_saddle_weeks": horse_saddle_weeks,
        "horse_saddle_months": horse_saddle_months,
        "intake_weeks": intake_weeks,
        "intake_months": intake_months,
        "open_months": open_months,
        "booking_alerts": booking_alerts,
        "booking_alert_count": len(booking_alerts),
    }

    return render(request, "ranch/office_dashboard.html", context)


def format_party_location(household):
    if not household:
        return ""
    city = (household.city or "").strip()
    state = (household.state or "").strip()
    country = (household.country or "").strip()

    is_us = not country or country.upper() in ["US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"]
    if is_us:
        if city and state:
            return f"{city}, {state}"
        elif city:
            return city
        elif state:
            return state
        return ""
    else:
        if city and country:
            return f"{city}, {country}"
        elif city and state:
            return f"{city}, {state}"
        elif city:
            return city
        elif country:
            return country
        return ""


def build_cabin_dining_parties(guests):
    from apps.clients.models import format_years_ordinal
    parties_dict = {}
    for guest in guests:
        res_id = guest.reservation_id
        if res_id not in parties_dict:
            household = guest.reservation.household if guest.reservation else None
            if not household and guest.client:
                membership = guest.client.household_memberships.select_related("household").first()
                if membership:
                    household = membership.household
            parties_dict[res_id] = {
                "reservation": guest.reservation,
                "household": household,
                "guests": [],
            }
        parties_dict[res_id]["guests"].append(guest)

    parties_list = []
    for party_info in parties_dict.values():
        party_guests = party_info["guests"]
        household = party_info["household"]
        reservation = party_info["reservation"]

        # Read highest return year of the clients in this cabin party
        max_years = max((g.years_count for g in party_guests), default=1)
        primary_years = format_years_ordinal(max_years)

        adults = []
        kids = []
        for g in party_guests:
            if g.years_count != max_years:
                g.inline_years = g.years_display
            else:
                g.inline_years = None

            if g.age_at_stay is not None and g.age_at_stay < 18:
                kids.append(g)
            else:
                adults.append(g)

        party_name = household.name if household and household.name else (
            reservation.primary_contact.full_name if reservation and reservation.primary_contact else "Guest Party"
        )
        location = format_party_location(household)

        parties_list.append({
            "reservation": reservation,
            "household": household,
            "party_name": party_name,
            "adults": adults,
            "kids": kids,
            "guests": party_guests,
            "primary_years": primary_years,
            "location": location,
        })

    return parties_list


@module_permission_required('Ranch', 'read')
def weekly_dining_guest_list_report(request):
    season_info = resolve_season_and_week(request)
    view_mode = season_info["view_mode"]
    period_start = season_info["period_start"]
    period_end = season_info["period_end"]
    week_start = season_info["week_start"]
    week_end = season_info["week_end"]
    month_start = season_info["month_start"]
    month_end = season_info["month_end"]
    month_end_display = season_info["month_end_display"]
    previous_week = season_info["previous_week"]
    next_week = season_info["next_week"]
    previous_month_year = season_info["previous_month_year"]
    previous_month_month = season_info["previous_month_month"]
    next_month_year = season_info["next_month_year"]
    next_month_month = season_info["next_month_month"]
    current_season = season_info["current_season"]
    categorized_seasons = season_info["categorized_seasons"]
    is_week_open_flag = season_info["is_week_open"]
    is_month_open_flag = season_info["is_month_open"]
    today = season_info["today"]

    reservations_this_week = Reservation.objects.filter(
        arrival_date__lt=period_end,
        departure_date__gt=period_start,
    ).exclude(
        status=Reservation.ReservationStatus.CANCELLED,
    )

    reservation_ids = reservations_this_week.values_list("id", flat=True)

    cabins = Cabin.objects.filter(
        reservation_guests__reservation_id__in=reservation_ids,
    ).distinct().order_by(
        "capacity",
        "sort_order",
        "name",
    )

    reservation_guests = ReservationGuest.objects.select_related(
        "reservation__household",
        "reservation__primary_contact",
        "client",
        "cabin",
    ).filter(
        reservation_id__in=reservation_ids,
    ).order_by(
        "cabin__capacity",
        "cabin__sort_order",
        "cabin__name",
        "client__last_name",
        "client__first_name",
    )

    cabin_sections = []

    for cabin in cabins:
        guests = [
            guest
            for guest in reservation_guests
            if guest.cabin_id == cabin.pk
        ]

        parties = build_cabin_dining_parties(guests)

        adults = []
        kids = []
        for guest in guests:
            if guest.age_at_stay is not None and guest.age_at_stay < 18:
                kids.append(guest)
            else:
                adults.append(guest)

        cabin_sections.append(
            {
                "cabin": cabin,
                "parties": parties,
                "adults": adults,
                "kids": kids,
                "guests": guests,
            }
        )

    unassigned_guests = [
        guest
        for guest in reservation_guests
        if guest.cabin_id is None
    ]

    if unassigned_guests:
        parties = build_cabin_dining_parties(unassigned_guests)

        adults = []
        kids = []
        for guest in unassigned_guests:
            if guest.age_at_stay is not None and guest.age_at_stay < 18:
                kids.append(guest)
            else:
                adults.append(guest)

        cabin_sections.append(
            {
                "cabin": None,
                "parties": parties,
                "adults": adults,
                "kids": kids,
                "guests": unassigned_guests,
            }
        )

    context = {
        "today": today,
        "view_mode": view_mode,
        "period_start": period_start,
        "period_end": period_end,
        "week_start": week_start,
        "week_end": week_end,
        "month_start": month_start,
        "month_end": month_end,
        "month_end_display": month_end_display,
        "target_year": season_info["target_year"],
        "target_month": season_info["target_month"],
        "previous_week": previous_week,
        "next_week": next_week,
        "previous_month_year": previous_month_year,
        "previous_month_month": previous_month_month,
        "next_month_year": next_month_year,
        "next_month_month": next_month_month,
        "current_season": current_season,
        "categorized_seasons": categorized_seasons,
        "is_week_open": is_week_open_flag,
        "is_month_open": is_month_open_flag,
        "cabin_sections": cabin_sections,
        "reservation_count": reservations_this_week.count(),
        "guest_count": reservation_guests.count(),
    }

    return render(request, "ranch/reports/weekly_dining_guest_list.html", context)


@module_permission_required('Ranch', 'read')
def weekly_special_requests_report(request):
    season_info = resolve_season_and_week(request)
    view_mode = season_info["view_mode"]
    period_start = season_info["period_start"]
    period_end = season_info["period_end"]
    week_start = season_info["week_start"]
    week_end = season_info["week_end"]
    month_start = season_info["month_start"]
    month_end = season_info["month_end"]
    month_end_display = season_info["month_end_display"]
    previous_week = season_info["previous_week"]
    next_week = season_info["next_week"]
    previous_month_year = season_info["previous_month_year"]
    previous_month_month = season_info["previous_month_month"]
    next_month_year = season_info["next_month_year"]
    next_month_month = season_info["next_month_month"]
    current_season = season_info["current_season"]
    categorized_seasons = season_info["categorized_seasons"]
    is_week_open_flag = season_info["is_week_open"]
    is_month_open_flag = season_info["is_month_open"]
    today = season_info["today"]

    reservations_this_week = Reservation.objects.filter(
        arrival_date__lt=period_end,
        departure_date__gt=period_start,
    ).exclude(
        status=Reservation.ReservationStatus.CANCELLED,
    ).select_related("primary_contact", "household")

    reservation_ids = reservations_this_week.values_list("id", flat=True)

    cabins = Cabin.objects.filter(
        reservation_guests__reservation_id__in=reservation_ids,
    ).distinct().order_by(
        "capacity",
        "sort_order",
        "name",
    )

    reservation_guests = ReservationGuest.objects.select_related(
        "reservation",
        "reservation__household",
        "reservation__primary_contact",
        "client",
        "cabin",
    ).filter(
        reservation_id__in=reservation_ids,
    ).order_by(
        "cabin__capacity",
        "cabin__sort_order",
        "cabin__name",
        "reservation__id",
        "client__last_name",
        "client__first_name",
    )

    def classify_item(line):
        lower = line.lower()
        if any(w in lower for w in ["allergic", "allergy", "nuts", "cilantro", "bananas", "peppers", "penicillin", "sulfad", "iodine", "minocin", "epi pen"]):
            return "highlight-allergy"
        if any(w in lower for w in ["does not eat", "no beef", "no lamb", "no seafood", "no dairy", "no cheese", "no fried food", "dairy sensitive", "vegetarian", "gluten free", "sensitive"]):
            return "highlight-dietary"
        if any(w in lower for w in ["diabetic", "stroke", "shoulder", "medical", "altitude", "hospital", "doctor"]):
            return "highlight-medical"
        if any(w in lower for w in ["shuttle", "flight", "casper", "sheridan", "gillette", "ua4", "ua5", "ramada", "hampton", "airport"]):
            return "highlight-shuttle"
        if any(w in lower for w in ["birthday", "bday"]):
            return "highlight-birthday"
        return "normal"

    cabin_sections = []

    for cabin in cabins:
        guests_in_cabin = [g for g in reservation_guests if g.cabin_id == cabin.pk]
        
        parties_dict = {}
        for guest in guests_in_cabin:
            res_id = guest.reservation_id
            if res_id not in parties_dict:
                household = guest.reservation.household
                if household and household.name:
                    party_name = household.name
                else:
                    party_name = guest.client.full_name

                addr1 = household.address_line_1 if household else ""
                addr2 = household.address_line_2 if household else ""
                city = household.city if household else ""
                state = household.state if household else ""
                postal = household.postal_code if household else ""
                country = household.country if household else ""

                if city and state:
                    csz = f"{city}, {state}"
                    if postal:
                        csz += f" {postal}"
                elif city:
                    csz = f"{city} {postal}".strip()
                elif postal:
                    csz = postal
                else:
                    csz = ""

                parties_dict[res_id] = {
                    "reservation": guest.reservation,
                    "household": household,
                    "party_name": party_name,
                    "address_line_1": addr1,
                    "address_line_2": addr2,
                    "city_state_zip": csz,
                    "country": country if country and country != "USA" else "",
                    "phones": set(),
                    "emails": set(),
                    "bullet_lines": [],
                    "guests": [],
                }

            party = parties_dict[res_id]
            party["guests"].append(guest)
            if guest.client.phone:
                party["phones"].add(guest.client.phone)
            if guest.client.email:
                party["emails"].add(guest.client.email)

            lines_to_add = []
            if guest.notes:
                for l in guest.notes.split("\n"):
                    l_str = l.strip()
                    if l_str and l_str not in lines_to_add:
                        lines_to_add.append(l_str)
            if guest.food_requests:
                for l in guest.food_requests.split("\n"):
                    l_str = l.strip()
                    if l_str and l_str not in lines_to_add:
                        lines_to_add.append(l_str)
            if guest.allergies:
                for l in guest.allergies.split("\n"):
                    l_str = l.strip()
                    if l_str and l_str not in lines_to_add:
                        lines_to_add.append(l_str)
            if guest.medical_notes:
                for l in guest.medical_notes.split("\n"):
                    l_str = l.strip()
                    if l_str and l_str not in lines_to_add:
                        lines_to_add.append(l_str)

            for line in lines_to_add:
                if line not in [item["text"] for item in party["bullet_lines"]]:
                    party["bullet_lines"].append({
                        "text": line,
                        "highlight_class": classify_item(line)
                    })

        parties_list = []
        for party in parties_dict.values():
            party["phones"] = sorted(list(party["phones"]))
            party["emails"] = sorted(list(party["emails"]))
            parties_list.append(party)

        cabin_sections.append({
            "cabin": cabin,
            "parties": parties_list,
            "guest_count": len(guests_in_cabin),
        })

    # Unassigned guests if any
    unassigned_guests = [g for g in reservation_guests if g.cabin_id is None]
    if unassigned_guests:
        parties_dict = {}
        for guest in unassigned_guests:
            res_id = guest.reservation_id
            if res_id not in parties_dict:
                household = guest.reservation.household
                party_name = household.name if household and household.name else guest.client.full_name
                parties_dict[res_id] = {
                    "reservation": guest.reservation,
                    "household": household,
                    "party_name": party_name,
                    "address_line_1": household.address_line_1 if household else "",
                    "address_line_2": household.address_line_2 if household else "",
                    "city_state_zip": f"{household.city}, {household.state} {household.postal_code}".strip() if household else "",
                    "country": household.country if household and household.country != "USA" else "",
                    "phones": set(),
                    "emails": set(),
                    "bullet_lines": [],
                    "guests": [],
                }
            party = parties_dict[res_id]
            party["guests"].append(guest)
            if guest.client.phone:
                party["phones"].add(guest.client.phone)
            if guest.client.email:
                party["emails"].add(guest.client.email)
            if guest.notes:
                for l in guest.notes.split("\n"):
                    l_str = l.strip()
                    if l_str and l_str not in [item["text"] for item in party["bullet_lines"]]:
                        party["bullet_lines"].append({"text": l_str, "highlight_class": classify_item(l_str)})

        parties_list = []
        for party in parties_dict.values():
            party["phones"] = sorted(list(party["phones"]))
            party["emails"] = sorted(list(party["emails"]))
            parties_list.append(party)

        cabin_sections.append({
            "cabin": None,
            "parties": parties_list,
            "guest_count": len(unassigned_guests),
        })

    context = {
        "today": today,
        "view_mode": view_mode,
        "period_start": period_start,
        "period_end": period_end,
        "week_start": week_start,
        "week_end": week_end,
        "month_start": month_start,
        "month_end": month_end,
        "month_end_display": month_end_display,
        "target_year": season_info["target_year"],
        "target_month": season_info["target_month"],
        "previous_week": previous_week,
        "next_week": next_week,
        "previous_month_year": previous_month_year,
        "previous_month_month": previous_month_month,
        "next_month_year": next_month_year,
        "next_month_month": next_month_month,
        "current_season": current_season,
        "categorized_seasons": categorized_seasons,
        "is_week_open": is_week_open_flag,
        "is_month_open": is_month_open_flag,
        "cabin_sections": cabin_sections,
        "reservation_count": reservations_this_week.count(),
        "guest_count": reservation_guests.count(),
    }

    return render(request, "ranch/reports/weekly_special_requests.html", context)


@module_permission_required('Ranch', 'read')
def weekly_horse_assignment_report(request):
    season_info = resolve_season_and_week(request)
    view_mode = season_info["view_mode"]
    period_start = season_info["period_start"]
    period_end = season_info["period_end"]
    week_start = season_info["week_start"]
    week_end = season_info["week_end"]
    month_start = season_info["month_start"]
    month_end = season_info["month_end"]
    month_end_display = season_info["month_end_display"]
    target_year = season_info["target_year"]
    target_month = season_info["target_month"]
    previous_week = season_info["previous_week"]
    next_week = season_info["next_week"]
    previous_month_year = season_info["previous_month_year"]
    previous_month_month = season_info["previous_month_month"]
    next_month_year = season_info["next_month_year"]
    next_month_month = season_info["next_month_month"]
    current_season = season_info["current_season"]
    categorized_seasons = season_info["categorized_seasons"]
    is_week_open_flag = season_info["is_week_open"]
    is_month_open_flag = season_info["is_month_open"]
    today = season_info["today"]

    if request.method == "POST":
        # Handle bulk save
        if "save_all" in request.POST:
            guest_ids = request.POST.getlist("guest_ids")
            for guest_id in guest_ids:
                guest = ReservationGuest.objects.filter(pk=guest_id).first()
                if guest:
                    form = HorseAssignmentForm(request.POST, instance=guest, prefix=f"guest_{guest_id}")
                    if form.is_valid():
                        form.save()
            if view_mode == "month":
                redirect_url = f"{request.path}?view=month&year={target_year}&month={target_month}"
            else:
                redirect_url = f"{request.path}?week={week_start.strftime('%Y-%m-%d')}"
            if current_season:
                redirect_url += f"&season={current_season.pk}"
            if request.GET.get("dept"):
                redirect_url += f"&dept={request.GET.get('dept')}"
            return redirect(redirect_url)
        
        # Keep single guest save for backward compatibility or direct posts
        guest_id = request.POST.get("guest_id")
        if guest_id:
            guest = get_object_or_404(ReservationGuest, pk=guest_id)
            form = HorseAssignmentForm(request.POST, instance=guest)
            if form.is_valid():
                form.save()
                if view_mode == "month":
                    redirect_url = f"{request.path}?view=month&year={target_year}&month={target_month}"
                else:
                    redirect_url = f"{request.path}?week={week_start.strftime('%Y-%m-%d')}"
                if current_season:
                    redirect_url += f"&season={current_season.pk}"
                if request.GET.get("dept"):
                    redirect_url += f"&dept={request.GET.get('dept')}"
                return redirect(redirect_url)

    reservations_this_week = Reservation.objects.filter(
        arrival_date__lt=period_end,
        departure_date__gt=period_start,
    ).exclude(
        status=Reservation.ReservationStatus.CANCELLED,
    )

    reservation_ids = reservations_this_week.values_list("id", flat=True)

    cabins = Cabin.objects.filter(
        reservation_guests__reservation_id__in=reservation_ids,
    ).distinct().order_by(
        "capacity",
        "sort_order",
        "name",
    )

    reservation_guests = ReservationGuest.objects.select_related(
        "reservation",
        "client",
        "cabin",
        "horse",
        "saddle",
    ).filter(
        reservation_id__in=reservation_ids,
    ).order_by(
        "cabin__capacity",
        "cabin__sort_order",
        "cabin__name",
        "client__last_name",
        "client__first_name",
    )

    # Fetch 3 most recent past horses and saddles for each guest
    for guest in reservation_guests:
        past_assignments = ReservationGuest.objects.filter(
            client=guest.client,
            reservation__arrival_date__lt=guest.reservation.arrival_date
        ).filter(
            Q(horse__isnull=False) | Q(saddle__isnull=False)
        ).select_related('horse', 'saddle', 'reservation').order_by('-reservation__arrival_date')[:3]
        
        guest.past_horses = [pa.horse for pa in past_assignments if pa.horse]
        guest.past_saddles = [pa.saddle for pa in past_assignments if pa.saddle]

    cabin_sections = []

    for cabin in cabins:
        guests = [
            guest
            for guest in reservation_guests
            if guest.cabin_id == cabin.pk
        ]
        
        # Prepare forms for each guest
        for guest in guests:
            guest.horse_form = HorseAssignmentForm(instance=guest, prefix=f"guest_{guest.pk}")

        cabin_sections.append(
            {
                "cabin": cabin,
                "guests": guests,
            }
        )

    unassigned_guests = [
        guest
        for guest in reservation_guests
        if guest.cabin_id is None
    ]
    
    if unassigned_guests:
        for guest in unassigned_guests:
            guest.horse_form = HorseAssignmentForm(instance=guest, prefix=f"guest_{guest.pk}")
            
        cabin_sections.append(
            {
                "cabin": None,
                "guests": unassigned_guests,
            }
        )

    context = {
        "today": today,
        "view_mode": view_mode,
        "period_start": period_start,
        "period_end": period_end,
        "week_start": week_start,
        "week_end": week_end,
        "month_start": month_start,
        "month_end": month_end,
        "month_end_display": month_end_display,
        "target_year": target_year,
        "target_month": target_month,
        "previous_week": previous_week,
        "next_week": next_week,
        "previous_month_year": previous_month_year,
        "previous_month_month": previous_month_month,
        "next_month_year": next_month_year,
        "next_month_month": next_month_month,
        "current_season": current_season,
        "categorized_seasons": categorized_seasons,
        "is_week_open": is_week_open_flag,
        "is_month_open": is_month_open_flag,
        "cabin_sections": cabin_sections,
        "unassigned_guests": unassigned_guests,
        "reservation_count": reservations_this_week.count(),
        "guest_count": reservation_guests.count(),
    }

    return render(request, "ranch/reports/weekly_horse_assignment.html", context)
