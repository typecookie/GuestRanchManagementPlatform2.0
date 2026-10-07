import calendar
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from apps.groups.decorators import module_permission_required

from apps.cabins.models import Cabin
from apps.clients.forms import ClientForm
from apps.clients.models import Client, TravelGroup, Household, TravelGroupMember, HouseholdMember
from django.http import JsonResponse

from .forms import OperatingSeasonForm, ReservationCabinForm, ReservationFlightForm, ReservationFlightFormSet, ReservationForm, ReservationGuestForm
from .models import OperatingSeason, Reservation, ReservationCabin, ReservationFlight, ReservationGuest
from .season_utils import (
    get_active_operating_seasons,
    get_active_season_for_date,
    get_current_or_upcoming_season,
    get_default_grid_year_month,
    get_default_season_dates,
    get_default_season,
    get_categorized_seasons,
    get_next_open_month,
    get_previous_open_month,
    get_next_month_tuple,
    get_previous_month_tuple,
    is_date_open,
    is_month_open,
    is_week_open,
    ensure_default_operating_season,
)


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
            open_status = is_week_open(week_start, week_end)
            weeks.append(
                {
                    "start": week_start,
                    "end": week_end,
                    "label": format_week_label(week_start, week_end),
                    "is_open": open_status,
                    "is_closed": not open_status,
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


@module_permission_required('Reservations', 'read')
def reservation_list(request):
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    reservation_type_filter = request.GET.get("reservation_type", "").strip()
    date_start = request.GET.get("date_start", "").strip()
    date_end = request.GET.get("date_end", "").strip()
    show_past = request.GET.get("show_past") == "true"
    season_filter = request.GET.get("season", "").strip()

    active_seasons = list(get_active_operating_seasons())
    categorized_seasons = get_categorized_seasons(date.today())

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

    if date_start:
        try:
            reservations = reservations.filter(arrival_date__gte=date_start)
        except (ValueError, ValidationError):
            pass

    if date_end:
        try:
            reservations = reservations.filter(departure_date__lte=date_end)
        except (ValueError, ValidationError):
            pass

    if season_filter:
        if season_filter == "open_season":
            if active_seasons:
                season_q = Q()
                for s in active_seasons:
                    season_q |= Q(arrival_date__lte=s.end_date, departure_date__gte=s.start_date)
                reservations = reservations.filter(season_q)
            else:
                reservations = reservations.filter(
                    Q(arrival_date__month__in=[6, 7, 8, 9]) | Q(departure_date__month__in=[6, 7, 8, 9])
                )
        elif season_filter.isdigit():
            try:
                selected_season = OperatingSeason.objects.get(pk=int(season_filter))
                reservations = reservations.filter(
                    arrival_date__lte=selected_season.end_date,
                    departure_date__gte=selected_season.start_date,
                )
            except OperatingSeason.DoesNotExist:
                pass

    # Default logic: Hide past reservations unless explicitly searching or showing them
    # Past reservations are those where departure_date < today
    is_lookup_active = search_query or date_start or date_end or season_filter

    if not show_past and not is_lookup_active:
        reservations = reservations.filter(departure_date__gte=date.today())

    if status_filter:
        reservations = reservations.filter(status=status_filter)

    if reservation_type_filter:
        reservations = reservations.filter(reservation_type=reservation_type_filter)

    context = {
        "reservations": reservations,
        "search_query": search_query,
        "status_filter": status_filter,
        "reservation_type_filter": reservation_type_filter,
        "date_start": date_start,
        "date_end": date_end,
        "show_past": show_past,
        "season_filter": season_filter,
        "active_seasons": active_seasons,
        "categorized_seasons": categorized_seasons,
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


@module_permission_required('Reservations', 'read')
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
    guest_form = ReservationGuestForm(reservation=reservation)

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

    tgs = TravelGroup.objects.none()
    if reservation.travel_group:
        tgs = TravelGroup.objects.filter(pk=reservation.travel_group.pk)
    
    hhs = Household.objects.none()
    if reservation.household:
        hhs = Household.objects.filter(pk=reservation.household.pk)
    
    if reservation.travel_group:
        # Include all households that are members of the travel group
        group_hhs = Household.objects.filter(
            travel_group_memberships__travel_group=reservation.travel_group
        )
        hhs = (hhs | group_hhs).distinct()

    flights = reservation.flights.all().order_by("airport", "flight_type", "flight_date", "flight_time", "created_at")
    arrival_flights = [f for f in flights if f.flight_type == ReservationFlight.FlightType.ARRIVAL]
    departure_flights = [f for f in flights if f.flight_type == ReservationFlight.FlightType.DEPARTURE]

    groups_dict = {}
    for flight in flights:
        airport_key = flight.airport.strip() if flight.airport else ""
        display_name = airport_key if airport_key else "Unspecified Airport"
        if airport_key not in groups_dict:
            groups_dict[airport_key] = {
                "airport": display_name,
                "arrival_flights": [],
                "departure_flights": [],
                "all_flights": [],
            }
        groups_dict[airport_key]["all_flights"].append(flight)
        if flight.flight_type == ReservationFlight.FlightType.ARRIVAL:
            groups_dict[airport_key]["arrival_flights"].append(flight)
        else:
            groups_dict[airport_key]["departure_flights"].append(flight)

    airport_flight_groups = list(groups_dict.values())

    flight_form = ReservationFlightForm(
        initial={
            "flight_date": reservation.arrival_date,
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
        "travel_groups": tgs,
        "households": hhs,
        "flights": flights,
        "arrival_flights": arrival_flights,
        "departure_flights": departure_flights,
        "airport_flight_groups": airport_flight_groups,
        "flight_form": flight_form,
    }

    return render(request, "reservations/reservation_detail.html", context)


@module_permission_required('Reservations', 'write')
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
        flight_formset = ReservationFlightFormSet(request.POST, prefix="flights")

        if form.is_valid() and flight_formset.is_valid():
            reservation = form.save()
            flight_formset.instance = reservation
            flight_formset.save()

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
        flight_formset = ReservationFlightFormSet(prefix="flights")

    context = {
        "form": form,
        "flight_formset": flight_formset,
        "form_title": "New Reservation",
        "form_subtitle": "Create a reservation for a guest stay, short stay, work crew, farrier, or cabin block.",
        "submit_label": "Create Reservation",
        "selected_cabin": selected_cabin,
    }

    return render(request, "reservations/reservation_form.html", context)


@module_permission_required('Reservations', 'write')
def reservation_update(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)

    if request.method == "POST":
        form = ReservationForm(request.POST, instance=reservation)
        flight_formset = ReservationFlightFormSet(request.POST, instance=reservation, prefix="flights")

        if form.is_valid() and flight_formset.is_valid():
            reservation = form.save()
            flight_formset.save()
            messages.success(request, f"Reservation {reservation.reservation_name} was updated.")
            return redirect("reservations:reservation_detail", pk=reservation.pk)
    else:
        form = ReservationForm(instance=reservation)
        flight_formset = ReservationFlightFormSet(instance=reservation, prefix="flights")

    context = {
        "reservation": reservation,
        "form": form,
        "flight_formset": flight_formset,
        "form_title": f"Edit {reservation.reservation_name}",
        "form_subtitle": "Update reservation dates, status, contact information, and notes.",
        "submit_label": "Save Reservation",
    }

    return render(request, "reservations/reservation_form.html", context)


@module_permission_required('Reservations', 'write')
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


@module_permission_required('Reservations', 'delete')
def reservation_cabin_delete(request, pk):
    cabin_assignment = get_object_or_404(ReservationCabin, pk=pk)
    reservation = cabin_assignment.reservation

    if request.method == "POST":
        cabin_assignment.delete()
        messages.success(request, "Cabin assignment was removed.")

    return redirect("reservations:reservation_detail", pk=reservation.pk)


@module_permission_required('Reservations', 'write')
def reservation_flight_create(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)

    if request.method == "POST":
        form = ReservationFlightForm(request.POST)

        if form.is_valid():
            flight = form.save(commit=False)
            flight.reservation = reservation
            if not flight.flight_date:
                flight.flight_date = (
                    reservation.arrival_date
                    if flight.flight_type == ReservationFlight.FlightType.ARRIVAL
                    else reservation.departure_date
                )

            try:
                flight.full_clean()
                flight.save()
                messages.success(request, f"{flight.get_flight_type_display()} flight was added.")
            except ValidationError as error:
                for message in error.messages:
                    messages.error(request, message)

            return redirect("reservations:reservation_detail", pk=reservation.pk)

        messages.error(request, "Please correct the flight form errors.")
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field.replace('_', ' ').title()}: {error}")

    return redirect("reservations:reservation_detail", pk=reservation.pk)


@module_permission_required('Reservations', 'write')
def reservation_flight_update(request, pk):
    flight = get_object_or_404(ReservationFlight.objects.select_related("reservation"), pk=pk)
    reservation = flight.reservation

    if request.method == "POST":
        form = ReservationFlightForm(request.POST, instance=flight)

        if form.is_valid():
            try:
                flight = form.save()
                messages.success(request, f"{flight.get_flight_type_display()} flight was updated.")
                return redirect("reservations:reservation_detail", pk=reservation.pk)
            except ValidationError as error:
                for message in error.messages:
                    messages.error(request, message)
        else:
            messages.error(request, "Please correct the flight form errors.")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        form = ReservationFlightForm(instance=flight)

    context = {
        "reservation": reservation,
        "flight": flight,
        "form": form,
        "form_title": f"Edit {flight.get_flight_type_display()} Flight",
        "form_subtitle": f"Update flight details for {reservation.reservation_name}.",
        "submit_label": "Save Flight",
    }

    return render(request, "reservations/reservation_flight_form.html", context)


@module_permission_required('Reservations', 'delete')
def reservation_flight_delete(request, pk):
    flight = get_object_or_404(ReservationFlight.objects.select_related("reservation"), pk=pk)
    reservation = flight.reservation

    if request.method == "POST":
        flight_desc = f"{flight.get_flight_type_display()} flight"
        flight.delete()
        messages.success(request, f"{flight_desc} was removed.")

    return redirect("reservations:reservation_detail", pk=reservation.pk)

@module_permission_required('Reservations', 'write')
@module_permission_required('Clients', 'write')
def reservation_guest_create_new_client(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)

    if request.method == "POST":
        form = ClientForm(request.POST)

        if form.is_valid():
            client = form.save()
            if reservation.travel_group_id:
                TravelGroupMember.objects.get_or_create(travel_group_id=reservation.travel_group_id, client=client)
            if reservation.household_id:
                HouseholdMember.objects.get_or_create(household_id=reservation.household_id, client=client)
            create_reservation_guest_from_client(reservation, client)
            messages.success(
                request,
                f"Client {client.display_name} was created and added to the reservation.",
            )
            return redirect("reservations:reservation_detail", pk=reservation.pk)
    else:
        form = ClientForm()

    context = {
        "form": form,
        "reservation": reservation,
        "form_title": "Add New Guest",
        "form_subtitle": f"Create a new client profile and add them to {reservation.reservation_name}.",
        "submit_label": "Create and Add Guest",
    }

    return render(request, "reservations/reservation_guest_new_client_form.html", context)


@module_permission_required('Reservations', 'write')
def reservation_guest_create(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)

    if request.method == "POST":
        form = ReservationGuestForm(request.POST, reservation=reservation)

        if form.is_valid():
            guest = form.save(commit=False)
            guest.reservation = reservation

            if not guest.cabin:
                guest.cabin = get_single_assigned_cabin(reservation)

            if guest.client and not guest.age_at_stay:
                if guest.client.date_of_birth:
                    guest.age_at_stay = calculate_age_at_date(
                        guest.client.date_of_birth,
                        reservation.arrival_date,
                    )
                elif guest.client.effective_age is not None:
                    guest.age_at_stay = guest.client.effective_age

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


@module_permission_required('Reservations', 'write')
def quick_add_reservation_item(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    reservation = get_object_or_404(Reservation, pk=pk)
    name = request.POST.get('name', '').strip()
    item_type = request.POST.get('type', 'client')
    travel_group_id = request.POST.get('travel_group_id')
    household_id = request.POST.get('household_id')

    if not name:
        return JsonResponse({'error': 'Name is required'}, status=400)

    if item_type == 'client':
        parts = name.split(' ', 1)
        if len(parts) > 1:
            first_name, last_name = parts
        else:
            first_name = parts[0]
            last_name = "-"

        client = Client.objects.create(first_name=first_name, last_name=last_name)

        if travel_group_id:
            TravelGroupMember.objects.get_or_create(travel_group_id=travel_group_id, client=client)
        elif reservation.travel_group_id:
            TravelGroupMember.objects.get_or_create(travel_group_id=reservation.travel_group_id, client=client)

        if household_id:
            HouseholdMember.objects.get_or_create(household_id=household_id, client=client)
        elif reservation.household_id:
            HouseholdMember.objects.get_or_create(household_id=reservation.household_id, client=client)

        create_reservation_guest_from_client(reservation, client)
        
        return JsonResponse({
            'id': client.pk,
            'name': client.full_name,
            'type': 'client',
            'reload': True
        })

    elif item_type == 'household':
        household = Household.objects.create(name=name)
        if travel_group_id:
            TravelGroupMember.objects.get_or_create(travel_group_id=travel_group_id, household=household)
        elif reservation.travel_group_id:
            TravelGroupMember.objects.get_or_create(travel_group_id=reservation.travel_group_id, household=household)
        
        reservation.household = household
        reservation.save(update_fields=['household'])
        
        return JsonResponse({
            'id': household.pk,
            'name': household.name,
            'type': 'household',
            'reload': True
        })

    elif item_type == 'travel_group':
        travel_group = TravelGroup.objects.create(name=name)
        reservation.travel_group = travel_group
        reservation.save(update_fields=['travel_group'])
        
        return JsonResponse({
            'id': travel_group.pk,
            'name': travel_group.name,
            'type': 'travel_group',
            'reload': True
        })

    return JsonResponse({'error': 'Invalid item type'}, status=400)


@module_permission_required('Reservations', 'write')
def reservation_guest_update(request, pk):
    guest = get_object_or_404(ReservationGuest, pk=pk)
    reservation = guest.reservation

    if request.method == "POST":
        form = ReservationGuestForm(request.POST, instance=guest, reservation=reservation)

        if form.is_valid():
            guest = form.save(commit=False)

            if not guest.cabin:
                guest.cabin = get_single_assigned_cabin(reservation)

            if guest.client and not guest.age_at_stay:
                if guest.client.date_of_birth:
                    guest.age_at_stay = calculate_age_at_date(
                        guest.client.date_of_birth,
                        reservation.arrival_date,
                    )
                elif guest.client.effective_age is not None:
                    guest.age_at_stay = guest.client.effective_age

            guest.save()
            messages.success(request, f"Guest information for {guest.client.display_name} was updated.")
            return redirect("reservations:reservation_detail", pk=reservation.pk)
    else:
        form = ReservationGuestForm(instance=guest, reservation=reservation)

    context = {
        "guest": guest,
        "reservation": reservation,
        "form": form,
        "form_title": f"Edit Guest Card: {guest.client.display_name}",
        "form_subtitle": f"Update stay-specific information for {reservation.reservation_name}.",
        "submit_label": "Save Guest Information",
    }

    return render(request, "reservations/reservation_guest_form.html", context)


@module_permission_required('Reservations', 'delete')
def reservation_guest_delete(request, pk):
    guest = get_object_or_404(ReservationGuest, pk=pk)
    reservation = guest.reservation

    if request.method == "POST":
        guest_name = guest.client.display_name
        guest.delete()
        messages.success(request, f"{guest_name} was removed from the reservation.")

    return redirect("reservations:reservation_detail", pk=reservation.pk)


def create_reservation_guest_from_client(reservation, client):
    age_at_stay = None
    if client.date_of_birth:
        age_at_stay = calculate_age_at_date(
            client.date_of_birth,
            reservation.arrival_date,
        )
    elif client.effective_age is not None:
        age_at_stay = client.effective_age

    assigned_cabin = get_single_assigned_cabin(reservation)
    is_riding = bool(client.is_rider and client.riding_level != 'non_rider')

    guest, created = ReservationGuest.objects.get_or_create(
        reservation=reservation,
        client=client,
        defaults={
            "cabin": assigned_cabin,
            "age_at_stay": age_at_stay,
            "is_riding": is_riding,
            "allergies": client.medical_notes,
            "food_requests": client.dietary_notes,
            "medical_notes": client.medical_notes,
        },
    )

    if not created and assigned_cabin and not guest.cabin:
        guest.cabin = assigned_cabin
        guest.save(update_fields=["cabin"])

    return guest, created


@module_permission_required('Reservations', 'write')
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


@module_permission_required('Reservations', 'write')
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

@module_permission_required('Reservations', 'write')
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


@module_permission_required('Reservations', 'write')
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

@module_permission_required('Reservations', 'read')
def reservation_grid(request):
    today = date.today()
    categorized_seasons = get_categorized_seasons(today)
    default_season = categorized_seasons["default_season"]

    season_param = request.GET.get("season", "").strip()
    selected_season = None
    if season_param and season_param.isdigit():
        selected_season = OperatingSeason.objects.filter(pk=int(season_param)).first()

    if selected_season:
        target_season = selected_season
        if "year" not in request.GET and "month" not in request.GET:
            if selected_season.contains_date(today):
                year = today.year
                month = today.month
            else:
                year = selected_season.start_date.year
                month = selected_season.start_date.month
        else:
            default_year, default_month = get_default_grid_year_month(today)
            year = int(request.GET.get("year", default_year))
            month = int(request.GET.get("month", default_month))
    else:
        if "year" in request.GET and "month" in request.GET:
            year = int(request.GET["year"])
            month = int(request.GET["month"])
            target_season = get_active_season_for_date(date(year, month, 1)) or get_current_or_upcoming_season(date(year, month, 1))
        elif "year" in request.GET:
            year = int(request.GET["year"])
            month = int(request.GET.get("month", 6))
            target_season = get_active_season_for_date(date(year, month, 1)) or get_current_or_upcoming_season(date(year, month, 1))
        else:
            year, month = get_default_grid_year_month(today)
            target_season = default_season

    filter_closed_param = request.GET.get("filter_closed")
    if filter_closed_param is None:
        filter_closed = True
    else:
        filter_closed = filter_closed_param.lower() not in ("false", "0", "no", "off")

    weeks = get_month_sunday_weeks(year, month)
    if filter_closed:
        weeks = [w for w in weeks if w["is_open"]]
        previous_year, previous_month = get_previous_open_month(year, month)
        next_year, next_month = get_next_open_month(year, month)
    else:
        previous_year, previous_month = get_previous_month_tuple(year, month)
        next_year, next_month = get_next_month_tuple(year, month)

    cabins = Cabin.objects.filter(is_active=True).order_by("capacity", "sort_order", "name")

    month_start = weeks[0]["start"] if weeks else date(year, month, 1)
    month_end = weeks[-1]["end"] if weeks else date(year, month, calendar.monthrange(year, month)[1])

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
                    "is_open": week["is_open"],
                    "is_closed": week["is_closed"],
                    "is_available": not positioned_assignments and week["is_open"],
                    "create_url": (
                        f"/reservations/new/"
                        f"?cabin={cabin.pk}"
                        f"&arrival_date={week['start'].isoformat()}"
                        f"&departure_date={week['end'].isoformat()}"
                    ),
                }
            )

        grid_rows.append(row)

    active_seasons = get_active_operating_seasons()
    current_season = target_season

    # Season months for quick navigation
    if active_seasons.filter(start_date__year__lte=year, end_date__year__gte=year).exists():
        year_seasons = active_seasons.filter(start_date__year__lte=year, end_date__year__gte=year)
        month_set = set()
        for s in year_seasons:
            s_month = s.start_date.month if s.start_date.year == year else 1
            e_month = s.end_date.month if s.end_date.year == year else 12
            for m in range(s_month, e_month + 1):
                month_set.add(m)
        season_months = sorted(list(month_set))
    else:
        season_months = [6, 7, 8, 9]

    season_nav_months = [
        {
            "month": m,
            "name": calendar.month_abbr[m],
            "full_name": calendar.month_name[m],
            "is_current": m == month,
        }
        for m in season_months
    ]

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
        "filter_closed": filter_closed,
        "active_seasons": active_seasons,
        "categorized_seasons": categorized_seasons,
        "current_season": current_season,
        "selected_season": selected_season,
        "season_nav_months": season_nav_months,
        "is_month_open": is_month_open(year, month),
        "today": today,
    }

    return render(request, "reservations/reservation_grid.html", context)


@module_permission_required('Reservations', 'read')
def operating_dates_list(request):
    seasons = OperatingSeason.objects.all().order_by("start_date")
    today = date.today()
    active_seasons = seasons.filter(is_active=True)

    current_season = get_active_season_for_date(today)
    upcoming_season = get_current_or_upcoming_season(today)
    is_open_today = is_date_open(today)

    context = {
        "seasons": seasons,
        "today": today,
        "active_seasons_count": active_seasons.count(),
        "current_season": current_season,
        "upcoming_season": upcoming_season,
        "is_open_today": is_open_today,
        "has_custom_seasons": seasons.exists(),
    }
    return render(request, "reservations/operating_dates_list.html", context)


@module_permission_required('Reservations', 'write')
def operating_season_create(request):
    if request.method == "POST":
        form = OperatingSeasonForm(request.POST)
        if form.is_valid():
            season = form.save()
            messages.success(request, f"Operating season '{season.name}' was created successfully.")
            return redirect("reservations:operating_dates_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        today = date.today()
        start_d, end_d = get_default_season_dates(today.year)
        form = OperatingSeasonForm(
            initial={
                "name": f"Summer Season {today.year}",
                "start_date": start_d,
                "end_date": end_d,
                "is_active": True,
            }
        )

    context = {
        "form": form,
        "form_title": "Add Operating Season",
        "form_subtitle": "Configure dates when the guest ranch is open for reservations.",
        "submit_label": "Save Operating Season",
    }
    return render(request, "reservations/operating_season_form.html", context)


@module_permission_required('Reservations', 'write')
def operating_season_update(request, pk):
    season = get_object_or_404(OperatingSeason, pk=pk)
    if request.method == "POST":
        form = OperatingSeasonForm(request.POST, instance=season)
        if form.is_valid():
            season = form.save()
            messages.success(request, f"Operating season '{season.name}' was updated successfully.")
            return redirect("reservations:operating_dates_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = OperatingSeasonForm(instance=season)

    context = {
        "form": form,
        "season": season,
        "form_title": f"Edit {season.name}",
        "form_subtitle": f"Update the open and close dates for {season.name}.",
        "submit_label": "Save Changes",
    }
    return render(request, "reservations/operating_season_form.html", context)


@module_permission_required('Reservations', 'delete')
def operating_season_delete(request, pk):
    season = get_object_or_404(OperatingSeason, pk=pk)
    if request.method == "POST":
        season_name = season.name
        season.delete()
        messages.success(request, f"Operating season '{season_name}' was removed.")
        return redirect("reservations:operating_dates_list")

    context = {
        "season": season,
        "title": f"Delete {season.name}",
        "confirm_message": f"Are you sure you want to delete '{season.name}' ({season.start_date} to {season.end_date})?",
    }
    return render(request, "reservations/operating_season_confirm_delete.html", context)


@module_permission_required('Reservations', 'write')
def operating_season_reset_defaults(request):
    if request.method == "POST":
        today = date.today()
        season = ensure_default_operating_season(today.year)
        messages.success(
            request,
            f"Standard operating season '{season.name}' (June 1 to September 30, {today.year}) is ready.",
        )
    return redirect("reservations:operating_dates_list")
    
@module_permission_required('Reservations', 'write')
def reservation_toggle_deposit_request(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)
    
    if request.method == "POST":
        reservation.deposit_request_sent = not reservation.deposit_request_sent
        reservation.save(update_fields=["deposit_request_sent", "updated_at"])
        
        status = "sent" if reservation.deposit_request_sent else "not sent"
        messages.success(request, f"Deposit request status updated to {status}.")
        
    return redirect("reservations:reservation_detail", pk=reservation.pk)


@module_permission_required('Reservations', 'write')
def reservation_toggle_deposit_received(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)
    
    if request.method == "POST":
        reservation.deposit_received = not reservation.deposit_received
        reservation.save(update_fields=["deposit_received", "updated_at"])
        
        status = "received" if reservation.deposit_received else "not received"
        messages.success(request, f"Deposit payment status updated to {status}.")
        
    return redirect("reservations:reservation_detail", pk=reservation.pk)


@module_permission_required('Reservations', 'write')
def reservation_guest_toggle_release(request, pk):
    guest = get_object_or_404(ReservationGuest.objects.select_related("reservation"), pk=pk)
    
    if request.method == "POST":
        guest.signed_release = not guest.signed_release
        guest.save(update_fields=["signed_release", "updated_at"])
        
        status = "signed" if guest.signed_release else "not signed"
        messages.success(request, f"Release form status for {guest.client.display_name} updated to {status}.")
        
    return redirect("reservations:reservation_detail", pk=guest.reservation.pk)
