from collections import Counter
from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from apps.groups.decorators import module_permission_required

from apps.reservations.models import Reservation, ReservationCabin, ReservationGuest
from apps.reservations.forms import HorseAssignmentForm
from apps.horses.models import Horse
from apps.cabins.models import Cabin
from apps.projects.models import Project

def get_current_sunday():
    today = date.today()
    days_since_sunday = (today.weekday() + 1) % 7
    return today - timedelta(days=days_since_sunday)


def parse_week_start(request):
    week_value = request.GET.get("week")

    if not week_value:
        return get_current_sunday()

    try:
        parsed_date = datetime.strptime(week_value, "%Y-%m-%d").date()
    except ValueError:
        return get_current_sunday()

    days_since_sunday = (parsed_date.weekday() + 1) % 7
    return parsed_date - timedelta(days=days_since_sunday)


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
    for current and upcoming weeks.
    """
    weeks_data = []

    for w_idx in range(num_weeks):
        w_start = week_start + timedelta(days=7 * w_idx)
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
        ).order_by("cabin__sort_order", "cabin__name", "client__last_name", "client__first_name")

        res_guest_map = {r.id: [] for r in reservations}

        horses_assigned = 0
        saddles_assigned = 0
        missing_info_count = 0
        total_riders = 0

        for g in guests:
            is_rider = g.is_riding and g.riding_experience != ReservationGuest.RidingExperience.NON_RIDER
            g.is_rider = is_rider

            missing_fields = []
            if is_rider:
                total_riders += 1
                if not g.height or not str(g.height).strip():
                    missing_fields.append("Height")
                if not g.weight or not str(g.weight).strip():
                    missing_fields.append("Weight")
                if not g.riding_experience or g.riding_experience == ReservationGuest.RidingExperience.UNKNOWN:
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
    for current and upcoming weeks.
    """
    weeks_data = []

    for w_idx in range(num_weeks):
        w_start = week_start + timedelta(days=7 * w_idx)
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
        ).order_by("cabin__sort_order", "cabin__name", "client__last_name", "client__first_name")

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


def build_booking_alerts(week_start):
    """
    Detects operational oddities and booking anomalies for the given week:
    - Multiple individuals / parties in a cabin without a TravelGroup
    - Multi-guest reservations without a Household or TravelGroup
    - Multiple active reservations overlapping in the same cabin
    - Cabin capacity overages
    - Multi-household reservations without a TravelGroup
    - Reservation guest count mismatches
    - Active reservations with zero guests attached
    - Cabin assignments outside reservation stay dates
    """
    week_end = week_start + timedelta(days=7)
    alerts = []

    reservations = Reservation.objects.select_related(
        "primary_contact", "household", "travel_group"
    ).prefetch_related(
        "guests__client__household_memberships__household",
        "guests__client__travel_group_memberships__travel_group",
        "guests__cabin",
        "cabin_assignments__cabin",
    ).filter(
        arrival_date__lt=week_end,
        departure_date__gt=week_start,
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
            if ca.arrival_date < week_end and ca.departure_date > week_start:
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

    for cabin in sorted(all_occupied_cabins, key=lambda c: (c.sort_order, c.name)):
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
                    "description": f"{len(c_reservations)} distinct unlinked reservations ({res_names_str}) are assigned to {cabin.name} in the week of {week_start.strftime('%b %d, %Y')}.",
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
    week_start = parse_week_start(request)
    week_end = week_start + timedelta(days=7)

    previous_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    reservations_this_week = Reservation.objects.select_related(
        "primary_contact",
        "household",
        "travel_group",
    ).filter(
        arrival_date__lt=week_end,
        departure_date__gt=week_start,
    ).exclude(
        status=Reservation.ReservationStatus.CANCELLED,
    ).order_by(
        "arrival_date",
        "reservation_name",
    )

    reservation_ids = reservations_this_week.values_list("id", flat=True)

    unassigned_guest_reservations = reservations_this_week.annotate(
        unassigned_guest_count=Count(
            "guests",
            filter=Q(guests__cabin__isnull=True),
        )
    ).filter(
        unassigned_guest_count__gt=0,
    )

    reservation_guests_this_week = ReservationGuest.objects.select_related(
        "reservation",
        "client",
        "cabin",
    ).filter(
        reservation_id__in=reservation_ids,
    )

    cabin_assignments_this_week = ReservationCabin.objects.select_related(
        "reservation",
        "cabin",
    ).filter(
        reservation_id__in=reservation_ids,
        arrival_date__lt=week_end,
        departure_date__gt=week_start,
    ).order_by(
        "cabin__sort_order",
        "cabin__name",
    )

    horse_saddle_weeks = build_weekly_horse_saddle_task(week_start, num_weeks=4)
    intake_weeks = build_weekly_intake_task(week_start, num_weeks=4)
    booking_alerts = build_booking_alerts(week_start)

    context = {
        "week_start": week_start,
        "week_end": week_end,
        "previous_week": previous_week,
        "next_week": next_week,
        "reservations_this_week": reservations_this_week,
        "unassigned_guest_reservations": unassigned_guest_reservations,
        "reservation_count": reservations_this_week.count(),
        "guest_count": reservation_guests_this_week.count(),
        "unassigned_guest_count": reservation_guests_this_week.filter(cabin__isnull=True).count(),
        "occupied_cabin_count": cabin_assignments_this_week.values("cabin").distinct().count(),
        "horse_saddle_weeks": horse_saddle_weeks,
        "intake_weeks": intake_weeks,
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
    week_start = parse_week_start(request)
    week_end = week_start + timedelta(days=7)

    previous_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    reservations_this_week = Reservation.objects.filter(
        arrival_date__lt=week_end,
        departure_date__gt=week_start,
    ).exclude(
        status=Reservation.ReservationStatus.CANCELLED,
    )

    reservation_ids = reservations_this_week.values_list("id", flat=True)

    cabins = Cabin.objects.filter(
        reservation_guests__reservation_id__in=reservation_ids,
    ).distinct().order_by(
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
        "week_start": week_start,
        "week_end": week_end,
        "previous_week": previous_week,
        "next_week": next_week,
        "cabin_sections": cabin_sections,
        "reservation_count": reservations_this_week.count(),
        "guest_count": reservation_guests.count(),
    }

    return render(request, "ranch/reports/weekly_dining_guest_list.html", context)


@module_permission_required('Ranch', 'read')
def weekly_special_requests_report(request):
    week_start = parse_week_start(request)
    week_end = week_start + timedelta(days=7)

    previous_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    reservations_this_week = Reservation.objects.filter(
        arrival_date__lt=week_end,
        departure_date__gt=week_start,
    ).exclude(
        status=Reservation.ReservationStatus.CANCELLED,
    ).select_related("primary_contact", "household")

    reservation_ids = reservations_this_week.values_list("id", flat=True)

    cabins = Cabin.objects.filter(
        reservation_guests__reservation_id__in=reservation_ids,
    ).distinct().order_by(
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
        "week_start": week_start,
        "week_end": week_end,
        "previous_week": previous_week,
        "next_week": next_week,
        "cabin_sections": cabin_sections,
        "reservation_count": reservations_this_week.count(),
        "guest_count": reservation_guests.count(),
    }

    return render(request, "ranch/reports/weekly_special_requests.html", context)


@module_permission_required('Ranch', 'read')
def weekly_horse_assignment_report(request):
    week_start = parse_week_start(request)
    week_end = week_start + timedelta(days=7)

    previous_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

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
            return redirect(f"{request.path}?week={week_start.strftime('%Y-%m-%d')}")
        
        # Keep single guest save for backward compatibility or direct posts
        guest_id = request.POST.get("guest_id")
        if guest_id:
            guest = get_object_or_404(ReservationGuest, pk=guest_id)
            form = HorseAssignmentForm(request.POST, instance=guest)
            if form.is_valid():
                form.save()
                return redirect(f"{request.path}?week={week_start.strftime('%Y-%m-%d')}")

    reservations_this_week = Reservation.objects.filter(
        arrival_date__lt=week_end,
        departure_date__gt=week_start,
    ).exclude(
        status=Reservation.ReservationStatus.CANCELLED,
    )

    reservation_ids = reservations_this_week.values_list("id", flat=True)

    cabins = Cabin.objects.filter(
        reservation_guests__reservation_id__in=reservation_ids,
    ).distinct().order_by(
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
        "week_start": week_start,
        "week_end": week_end,
        "previous_week": previous_week,
        "next_week": next_week,
        "cabin_sections": cabin_sections,
        "reservation_count": reservations_this_week.count(),
        "guest_count": reservation_guests.count(),
    }

    return render(request, "ranch/reports/weekly_horse_assignment.html", context)
