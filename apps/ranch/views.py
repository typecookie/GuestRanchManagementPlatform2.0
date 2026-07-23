from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from apps.groups.decorators import module_permission_required

from apps.reservations.models import Reservation, ReservationCabin, ReservationGuest
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
    }

    return render(request, "ranch/office_dashboard.html", context)


@module_permission_required('Ranch', 'read')
def weekly_dining_guest_list_report(request):
    week_start = parse_week_start(request)
    week_end = week_start + timedelta(days=7)

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
                "adults": adults,
                "kids": kids,
                "guests": unassigned_guests,
            }
        )

    context = {
        "week_start": week_start,
        "week_end": week_end,
        "cabin_sections": cabin_sections,
        "reservation_count": reservations_this_week.count(),
        "guest_count": reservation_guests.count(),
    }

    return render(request, "ranch/reports/weekly_dining_guest_list.html", context)
