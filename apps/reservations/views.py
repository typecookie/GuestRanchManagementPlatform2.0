import calendar
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.cabins.models import Cabin

from .forms import ReservationCabinForm, ReservationForm, ReservationGuestForm
from .models import Reservation, ReservationCabin, ReservationGuest


def format_week_label(week_start, week_end):
    display_end = week_end - timedelta(days=1)
    return f"{week_start.strftime('%b')} {week_start.day} - {display_end.strftime('%b')} {display_end.day}"


def get_month_sunday_weeks(year, month):
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    days_since_sunday = (first_day.weekday() + 1) % 7
    current_sunday = first_day - timedelta(days=days_since_sunday)

    weeks = []

    while current_sunday <= last_day:
        week_start = current_sunday
        week_end = current_sunday + timedelta(days=7)

        if week_end > first_day and week_start <= last_day:
            weeks.append(
                {
                    "start": week_start,
                    "end": week_end,
                    "label": format_week_label(week_start, week_end),
                }
            )

        current_sunday += timedelta(days=7)

    return weeks


def get_previous_month(year, month):
    if month == 1:
        return year - 1, 12

    return year, month - 1


def get_next_month(year, month):
    if month == 12:
        return year + 1, 1

    return year, month + 1


def get_next_sunday():
    today = date.today()
    days_until_sunday = (6 - today.weekday()) % 7

    if days_until_sunday == 0:
        return today

    return today + timedelta(days=days_until_sunday)


@login_required
def reservation_list(request):
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    reservation_type_filter = request.GET.get("reservation_type", "").strip()

    reservations = Reservation.objects.select_related(
        "primary_contact",
        "household",
        "travel_group",
    ).all()

    if search_query:
        reservations = reservations.filter(
            Q(reservation_name__icontains=search_query)
            | Q(primary_contact__first_name__icontains=search_query)
            | Q(primary_contact__middle_name__icontains=search_query)
            | Q(primary_contact__last_name__icontains=search_query)
            | Q(household__name__icontains=search_query)
            | Q(travel_group__name__icontains=search_query)
            | Q(notes__icontains=search_query)
            | Q(internal_notes__icontains=search_query)
        )

    if status_filter:
        reservations = reservations.filter(status=status_filter)

    if reservation_type_filter:
        reservations = reservations.filter(reservation_type=reservation_type_filter)

    context = {
        "reservations": reservations,
        "search_query": search_query,
        "status_filter": status_filter,
        "reservation_type_filter": reservation_type_filter,
        "total_reservations": Reservation.objects.count(),
        "penciled_reservations": Reservation.objects.filter(
            status=Reservation.ReservationStatus.PENCILED
        ).count(),
        "confirmed_reservations": Reservation.objects.filter(
            status=Reservation.ReservationStatus.CONFIRMED
        ).count(),
        "current_results": reservations.count(),
        "status_choices": Reservation.ReservationStatus.choices,
        "reservation_type_choices": Reservation.ReservationType.choices,
    }

    return render(request, "reservations/reservation_list.html", context)


@login_required
def reservation_detail(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related(
            "primary_contact",
            "household",
            "travel_group",
        ),
        pk=pk,
    )

    cabin_assignments = reservation.cabin_assignments.select_related("cabin")
    reservation_guests = reservation.guests.select_related("client", "cabin")
    guest_form = ReservationGuestForm()

    cabin_guest_sections = []

    for assignment in cabin_assignments:
        cabin_guests = reservation_guests.filter(cabin=assignment.cabin)

        cabin_guest_sections.append(
            {
                "assignment": assignment,
                "cabin": assignment.cabin,
                "guests": cabin_guests,
            }
        )

    unassigned_guests = reservation_guests.filter(cabin__isnull=True)

    cabin_form = ReservationCabinForm(
        initial={
            "arrival_date": reservation.arrival_date,
            "departure_date": reservation.departure_date,
        }
    )

    context = {
        "reservation": reservation,
        "cabin_assignments": cabin_assignments,
        "cabin_form": cabin_form,
        "reservation_guests": reservation_guests,
        "guest_form": guest_form,
        "cabin_guest_sections": cabin_guest_sections,
        "unassigned_guests": unassigned_guests,
    }

    return render(request, "reservations/reservation_detail.html", context)


@login_required
def reservation_create(request):
    next_sunday = get_next_sunday()
    following_sunday = next_sunday + timedelta(days=7)

    cabin_id = request.GET.get("cabin") or request.POST.get("grid_cabin_id")

    initial = {
        "arrival_date": request.GET.get("arrival_date", next_sunday),
        "departure_date": request.GET.get("departure_date", following_sunday),
    }

    selected_cabin = None

    if cabin_id:
        selected_cabin = Cabin.objects.filter(pk=cabin_id).first()

    if request.method == "POST":
        form = ReservationForm(request.POST)

        if form.is_valid():
            reservation = form.save()

            if selected_cabin:
                cabin_assignment = ReservationCabin(
                    reservation=reservation,
                    cabin=selected_cabin,
                    arrival_date=reservation.arrival_date,
                    departure_date=reservation.departure_date,
                )

                try:
                    cabin_assignment.full_clean()
                    cabin_assignment.save()
                    messages.success(
                        request,
                        f"Reservation {reservation.reservation_name} was created and assigned to {selected_cabin.name}.",
                    )
                except ValidationError as error:
                    messages.warning(
                        request,
                        f"Reservation was created, but the cabin assignment could not be added: {' '.join(error.messages)}",
                    )

                return redirect("reservations:reservation_detail", pk=reservation.pk)

            messages.success(request, f"Reservation {reservation.reservation_name} was created.")
            return redirect("reservations:reservation_detail", pk=reservation.pk)
    else:
        form = ReservationForm(initial=initial)

    context = {
        "form": form,
        "form_title": "New Reservation",
        "form_subtitle": "Create a reservation for a guest stay, short stay, work crew, farrier, or cabin block.",
        "submit_label": "Create Reservation",
        "selected_cabin": selected_cabin,
    }

    return render(request, "reservations/reservation_form.html", context)


@login_required
def reservation_update(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)

    if request.method == "POST":
        form = ReservationForm(request.POST, instance=reservation)

        if form.is_valid():
            reservation = form.save()
            messages.success(request, f"Reservation {reservation.reservation_name} was updated.")
            return redirect("reservations:reservation_detail", pk=reservation.pk)
    else:
        form = ReservationForm(instance=reservation)

    context = {
        "reservation": reservation,
        "form": form,
        "form_title": f"Edit {reservation.reservation_name}",
        "form_subtitle": "Update reservation dates, status, contact information, and notes.",
        "submit_label": "Save Reservation",
    }

    return render(request, "reservations/reservation_form.html", context)


@login_required
def reservation_cabin_create(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)

    if request.method == "POST":
        form = ReservationCabinForm(request.POST)

        if form.is_valid():
            cabin_assignment = form.save(commit=False)
            cabin_assignment.reservation = reservation

            try:
                cabin_assignment.full_clean()
                cabin_assignment.save()
                messages.success(request, "Cabin assignment was added.")
            except ValidationError as error:
                for message in error.messages:
                    messages.error(request, message)

            return redirect("reservations:reservation_detail", pk=reservation.pk)

        messages.error(request, "Please correct the cabin assignment form errors.")

    return redirect("reservations:reservation_detail", pk=reservation.pk)


@login_required
def reservation_cabin_delete(request, pk):
    cabin_assignment = get_object_or_404(ReservationCabin, pk=pk)
    reservation = cabin_assignment.reservation

    if request.method == "POST":
        cabin_assignment.delete()
        messages.success(request, "Cabin assignment was removed.")

    return redirect("reservations:reservation_detail", pk=reservation.pk)

@login_required
def reservation_guest_create(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)

    if request.method == "POST":
        form = ReservationGuestForm(request.POST)

        if form.is_valid():
            guest = form.save(commit=False)
            guest.reservation = reservation

            if not guest.cabin:
                guest.cabin = get_single_assigned_cabin(reservation)

            if guest.client and guest.client.date_of_birth and not guest.age_at_stay:
                guest.age_at_stay = calculate_age_at_date(
                    guest.client.date_of_birth,
                    reservation.arrival_date,
                )

            try:
                guest.full_clean()
                guest.save()
                messages.success(request, f"{guest.client.display_name} was added to the reservation.")
            except ValidationError as error:
                for message in error.messages:
                    messages.error(request, message)

            return redirect("reservations:reservation_detail", pk=reservation.pk)

        messages.error(request, "Guest could not be added. Please check the guest form.")
        messages.error(request, form.errors.as_text())

    return redirect("reservations:reservation_detail", pk=reservation.pk)


@login_required
def reservation_guest_update(request, pk):
    guest = get_object_or_404(ReservationGuest, pk=pk)
    reservation = guest.reservation

    if request.method == "POST":
        form = ReservationGuestForm(request.POST, instance=guest)

        if form.is_valid():
            guest = form.save(commit=False)

            if not guest.cabin:
                guest.cabin = get_single_assigned_cabin(reservation)

            if guest.client and guest.client.date_of_birth and not guest.age_at_stay:
                guest.age_at_stay = calculate_age_at_date(
                    guest.client.date_of_birth,
                    reservation.arrival_date,
                )

            guest.save()
            messages.success(request, f"Guest information for {guest.client.display_name} was updated.")
            return redirect("reservations:reservation_detail", pk=reservation.pk)
    else:
        form = ReservationGuestForm(instance=guest)

    context = {
        "guest": guest,
        "reservation": reservation,
        "form": form,
        "form_title": f"Edit Guest Card: {guest.client.display_name}",
        "form_subtitle": f"Update stay-specific information for {reservation.reservation_name}.",
        "submit_label": "Save Guest Information",
    }

    return render(request, "reservations/reservation_guest_form.html", context)


@login_required
def reservation_guest_delete(request, pk):
    guest = get_object_or_404(ReservationGuest, pk=pk)
    reservation = guest.reservation

    if request.method == "POST":
        guest_name = guest.client.display_name
        guest.delete()
        messages.success(request, f"{guest_name} was removed from the reservation.")

    return redirect("reservations:reservation_detail", pk=reservation.pk)


def create_reservation_guest_from_client(reservation, client):
    age_at_stay = calculate_age_at_date(
        client.date_of_birth,
        reservation.arrival_date,
    )
    assigned_cabin = get_single_assigned_cabin(reservation)

    guest, created = ReservationGuest.objects.get_or_create(
        reservation=reservation,
        client=client,
        defaults={
            "cabin": assigned_cabin,
            "age_at_stay": age_at_stay,
            "riding_experience": client.riding_level,
            "allergies": client.medical_notes,
            "food_requests": client.dietary_notes,
            "medical_notes": client.medical_notes,
        },
    )

    if not created and assigned_cabin and not guest.cabin:
        guest.cabin = assigned_cabin
        guest.save(update_fields=["cabin"])

    return guest, created


@login_required
def reservation_add_household_guests(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)

    if request.method != "POST":
        return redirect("reservations:reservation_detail", pk=reservation.pk)

    if not reservation.household:
        messages.error(request, "This reservation is not linked to a household.")
        return redirect("reservations:reservation_detail", pk=reservation.pk)

    memberships = reservation.household.memberships.select_related("client")

    created_count = 0
    skipped_count = 0

    for membership in memberships:
        _, created = create_reservation_guest_from_client(
            reservation=reservation,
            client=membership.client,
        )

        if created:
            created_count += 1
        else:
            skipped_count += 1

    if created_count:
        messages.success(request, f"{created_count} household guest(s) were added to the reservation.")

    if skipped_count:
        messages.info(request, f"{skipped_count} household guest(s) were already on the reservation.")

    if not created_count and not skipped_count:
        messages.warning(request, "No household members were found to add.")

    return redirect("reservations:reservation_detail", pk=reservation.pk)


@login_required
def reservation_add_travel_group_guests(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)

    if request.method != "POST":
        return redirect("reservations:reservation_detail", pk=reservation.pk)

    if not reservation.travel_group:
        messages.error(request, "This reservation is not linked to a travel group.")
        return redirect("reservations:reservation_detail", pk=reservation.pk)

    travel_group_memberships = reservation.travel_group.memberships.select_related(
        "client",
        "household",
    )

    clients_to_add = []

    for membership in travel_group_memberships:
        if membership.client:
            clients_to_add.append(membership.client)

        if membership.household:
            household_memberships = membership.household.memberships.select_related("client")

            for household_membership in household_memberships:
                clients_to_add.append(household_membership.client)

    unique_clients = []
    seen_client_ids = set()

    for client in clients_to_add:
        if client.pk not in seen_client_ids:
            unique_clients.append(client)
            seen_client_ids.add(client.pk)

    created_count = 0
    skipped_count = 0

    for client in unique_clients:
        _, created = create_reservation_guest_from_client(
            reservation=reservation,
            client=client,
        )

        if created:
            created_count += 1
        else:
            skipped_count += 1

    if created_count:
        messages.success(request, f"{created_count} travel group guest(s) were added to the reservation.")

    if skipped_count:
        messages.info(request, f"{skipped_count} travel group guest(s) were already on the reservation.")

    if not created_count and not skipped_count:
        messages.warning(request, "No travel group members were found to add.")

    return redirect("reservations:reservation_detail", pk=reservation.pk)

def calculate_age_at_date(date_of_birth, target_date):
    if not date_of_birth or not target_date:
        return None

    age = target_date.year - date_of_birth.year

    has_had_birthday = (
        target_date.month,
        target_date.day,
    ) >= (
        date_of_birth.month,
        date_of_birth.day,
    )

    if not has_had_birthday:
        age -= 1

    return age


def get_single_assigned_cabin(reservation):
    cabin_assignments = reservation.cabin_assignments.select_related("cabin")

    if cabin_assignments.count() == 1:
        return cabin_assignments.first().cabin

    return None


def get_assignment_week_position(assignment, week):
    visible_start = max(assignment.arrival_date, week["start"])
    visible_end = min(assignment.departure_date, week["end"])

    occupied_days = max((visible_end - visible_start).days, 0)
    offset_days = max((visible_start - week["start"]).days, 0)

    left_percent = round((offset_days / 7) * 100, 2)
    width_percent = round((occupied_days / 7) * 100, 2)

    return {
        "visible_start": visible_start,
        "visible_end": visible_end,
        "left_percent": left_percent,
        "width_percent": width_percent,
        "occupied_days": occupied_days,
        "is_partial": left_percent > 0 or width_percent < 100,
    }

@login_required
def reservation_guest_assign_cabin(request, pk):
    guest = get_object_or_404(
        ReservationGuest.objects.select_related("reservation"),
        pk=pk,
    )
    reservation = guest.reservation

    if request.method == "POST":
        cabin_id = request.POST.get("cabin")

        if not cabin_id:
            messages.error(request, "Please choose a cabin.")
            return redirect("reservations:reservation_detail", pk=reservation.pk)

        cabin_assignment = reservation.cabin_assignments.filter(cabin_id=cabin_id).first()

        if not cabin_assignment:
            messages.error(request, "That cabin is not assigned to this reservation.")
            return redirect("reservations:reservation_detail", pk=reservation.pk)

        guest.cabin = cabin_assignment.cabin
        guest.save(update_fields=["cabin", "updated_at"])

        messages.success(
            request,
            f"{guest.client.display_name} was assigned to {cabin_assignment.cabin.name}.",
        )

    return redirect("reservations:reservation_detail", pk=reservation.pk)


@login_required
def reservation_guest_unassign_cabin(request, pk):
    guest = get_object_or_404(
        ReservationGuest.objects.select_related("reservation", "client", "cabin"),
        pk=pk,
    )
    reservation = guest.reservation

    if request.method == "POST":
        guest_name = guest.client.display_name
        guest.cabin = None
        guest.save(update_fields=["cabin", "updated_at"])

        messages.success(request, f"{guest_name} was moved to unassigned guests.")

    return redirect("reservations:reservation_detail", pk=reservation.pk)

@login_required
def reservation_grid(request):
    today = date.today()

    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    weeks = get_month_sunday_weeks(year, month)
    previous_year, previous_month = get_previous_month(year, month)
    next_year, next_month = get_next_month(year, month)

    cabins = Cabin.objects.filter(is_active=True).order_by("sort_order", "name")

    month_start = weeks[0]["start"]
    month_end = weeks[-1]["end"]

    cabin_assignments = ReservationCabin.objects.select_related(
        "reservation",
        "cabin",
    ).filter(
        cabin__in=cabins,
        arrival_date__lt=month_end,
        departure_date__gt=month_start,
    ).exclude(
        reservation__status=Reservation.ReservationStatus.CANCELLED,
    )

    grid_rows = []

    for cabin in cabins:
        row = {
            "cabin": cabin,
            "cells": [],
        }

        for week in weeks:
            week_assignments = cabin_assignments.filter(
                cabin=cabin,
                arrival_date__lt=week["end"],
                departure_date__gt=week["start"],
            ).order_by("arrival_date", "departure_date")

            positioned_assignments = []

            for assignment in week_assignments:
                positioned_assignments.append(
                    {
                        "assignment": assignment,
                        "reservation": assignment.reservation,
                        "position": get_assignment_week_position(assignment, week),
                    }
                )

            row["cells"].append(
                {
                    "week": week,
                    "assignments": positioned_assignments,
                    "is_available": not positioned_assignments,
                    "create_url": (
                        f"/reservations/new/"
                        f"?cabin={cabin.pk}"
                        f"&arrival_date={week['start'].isoformat()}"
                        f"&departure_date={week['end'].isoformat()}"
                    ),
                }
            )

        grid_rows.append(row)

    context = {
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "weeks": weeks,
        "grid_rows": grid_rows,
        "previous_year": previous_year,
        "previous_month": previous_month,
        "next_year": next_year,
        "next_month": next_month,
    }

    return render(request, "reservations/reservation_grid.html", context)
