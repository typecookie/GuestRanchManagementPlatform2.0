import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from apps.groups.decorators import module_permission_required

from .forms import (
    ClientForm,
    ClientNoteForm,
    HouseholdForm,
    HouseholdMemberForm,
    TravelGroupForm,
    TravelGroupMemberForm,
)
from .models import Client, Household, HouseholdMember, TravelGroup, TravelGroupMember
from apps.reservations.models import Reservation, ReservationGuest
from apps.cabins.models import Cabin


@module_permission_required('Clients', 'read')
def client_list(request):
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    client_type_filter = request.GET.get("client_type", "").strip()
    riding_level_filter = request.GET.get("riding_level", "").strip()

    clients = Client.objects.all()

    if search_query:
        clients = clients.filter(
            Q(first_name__icontains=search_query)
            | Q(middle_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(preferred_name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(phone__icontains=search_query)
            | Q(alternate_phone__icontains=search_query)
        )

    if status_filter == "active":
        clients = clients.filter(is_active=True)
    elif status_filter == "inactive":
        clients = clients.filter(is_active=False)

    if client_type_filter:
        clients = clients.filter(client_type=client_type_filter)

    if riding_level_filter:
        clients = clients.filter(riding_level=riding_level_filter)

    context = {
        "clients": clients,
        "search_query": search_query,
        "status_filter": status_filter,
        "client_type_filter": client_type_filter,
        "riding_level_filter": riding_level_filter,
        "total_clients": Client.objects.count(),
        "active_clients": Client.objects.filter(is_active=True).count(),
        "inactive_clients": Client.objects.filter(is_active=False).count(),
        "search_result_count": clients.count(),
        "client_type_choices": Client.ClientType.choices,
        "riding_level_choices": Client.RidingLevel.choices,
    }

    return render(request, "clients/client_list.html", context)


@module_permission_required('Clients', 'read')
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)

    household_memberships = client.household_memberships.select_related("household")
    travel_group_memberships = client.travel_group_memberships.select_related("travel_group")
    notes = client.notes.select_related("created_by")
    note_form = ClientNoteForm()

    context = {
        "client": client,
        "household_memberships": household_memberships,
        "travel_group_memberships": travel_group_memberships,
        "notes": notes,
        "note_form": note_form,
    }

    return render(request, "clients/client_detail.html", context)


@module_permission_required('Clients', 'write')
def client_create(request):
    if request.method == "POST":
        form = ClientForm(request.POST)

        if form.is_valid():
            client = form.save()
            messages.success(request, f"Client {client.display_name} was created.")
            return redirect("clients:client_detail", pk=client.pk)
    else:
        form = ClientForm()

    context = {
        "form": form,
        "form_title": "Add Client",
        "form_subtitle": "Create a new guest profile for the ranch contact book.",
        "submit_label": "Create Client",
    }

    return render(request, "clients/client_form.html", context)


@module_permission_required('Clients', 'write')
def client_update(request, pk):
    client = get_object_or_404(Client, pk=pk)

    if request.method == "POST":
        form = ClientForm(request.POST, instance=client)

        if form.is_valid():
            client = form.save()
            messages.success(request, f"Client {client.display_name} was updated.")
            return redirect("clients:client_detail", pk=client.pk)
    else:
        form = ClientForm(instance=client)

    context = {
        "client": client,
        "form": form,
        "form_title": f"Edit {client.display_name}",
        "form_subtitle": "Update contact information, preferences, and guest notes.",
        "submit_label": "Save Client",
    }

    return render(request, "clients/client_form.html", context)


@module_permission_required('Clients', 'write')
def client_note_create(request, pk):
    client = get_object_or_404(Client, pk=pk)

    if request.method == "POST":
        form = ClientNoteForm(request.POST)

        if form.is_valid():
            note = form.save(commit=False)
            note.client = client
            note.created_by = request.user
            note.save()

            messages.success(request, "Client note was added.")
            return redirect("clients:client_detail", pk=client.pk)

        messages.error(request, "Please correct the note form errors.")

    return redirect("clients:client_detail", pk=client.pk)


@module_permission_required('Clients', 'write')
def household_create(request):
    if request.method == "POST":
        form = HouseholdForm(request.POST)

        if form.is_valid():
            household = form.save()
            messages.success(request, f"Household {household.name} was created.")
            return redirect("clients:household_detail", pk=household.pk)
    else:
        form = HouseholdForm()

    context = {
        "form": form,
        "form_title": "Add Household",
        "form_subtitle": "Create a family unit or household for related guests.",
        "submit_label": "Create Household",
    }

    return render(request, "clients/household_form.html", context)


@module_permission_required('Clients', 'read')
def household_detail(request, pk):
    household = get_object_or_404(Household, pk=pk)

    memberships = household.memberships.select_related("client")
    travel_group_memberships = household.travel_group_memberships.select_related("travel_group")
    member_form = HouseholdMemberForm()
    member_form.fields['client'].widget.attrs['data-create-url'] = reverse('clients:household_member_create_new_client', args=[household.pk])

    context = {
        "household": household,
        "memberships": memberships,
        "travel_group_memberships": travel_group_memberships,
        "member_form": member_form,
    }

    return render(request, "clients/household_detail.html", context)


@module_permission_required('Clients', 'write')
def household_update(request, pk):
    household = get_object_or_404(Household, pk=pk)

    if request.method == "POST":
        form = HouseholdForm(request.POST, instance=household)

        if form.is_valid():
            household = form.save()
            messages.success(request, f"Household {household.name} was updated.")
            return redirect("clients:household_detail", pk=household.pk)
    else:
        form = HouseholdForm(instance=household)

    context = {
        "household": household,
        "form": form,
        "form_title": f"Edit {household.name}",
        "form_subtitle": "Update household contact, address, and notes.",
        "submit_label": "Save Household",
    }

    return render(request, "clients/household_form.html", context)


@module_permission_required('Clients', 'write')
def household_member_create(request, pk):
    household = get_object_or_404(Household, pk=pk)

    if request.method == "POST":
        form = HouseholdMemberForm(request.POST)

        if form.is_valid():
            membership = form.save(commit=False)
            membership.household = household
            membership.save()

            if membership.is_primary_contact:
                household.primary_contact = membership.client

            if membership.is_billing_contact:
                household.billing_contact = membership.client

            household.save()

            messages.success(request, f"{membership.client.display_name} was added to {household.name}.")
            return redirect("clients:household_detail", pk=household.pk)

        messages.error(request, "Please correct the household member form errors.")

    return redirect("clients:household_detail", pk=household.pk)


@module_permission_required('Clients', 'write')
def household_member_create_new_client(request, pk):
    household = get_object_or_404(Household, pk=pk)

    if request.method == "POST":
        form = ClientForm(request.POST)

        if form.is_valid():
            client = form.save()
            HouseholdMember.objects.create(
                household=household,
                client=client,
                relationship=HouseholdMember.Relationship.UNKNOWN
            )
            messages.success(request, f"Client {client.display_name} was created and added to {household.name}.")
            return redirect("clients:household_detail", pk=household.pk)
    else:
        form = ClientForm()

    context = {
        "form": form,
        "household": household,
        "form_title": "Add New Member to Household",
        "form_subtitle": f"Create a new client profile and add them to {household.name}.",
        "submit_label": "Create and Add Member",
    }

    return render(request, "clients/client_form.html", context)


@module_permission_required('Clients', 'delete')
def household_member_delete(request, pk):
    membership = get_object_or_404(HouseholdMember, pk=pk)
    household = membership.household

    if request.method == "POST":
        client_name = membership.client.display_name
        membership.delete()

        if household.primary_contact_id == membership.client_id:
            household.primary_contact = None

        if household.billing_contact_id == membership.client_id:
            household.billing_contact = None

        household.save()

        messages.success(request, f"{client_name} was removed from {household.name}.")

    return redirect("clients:household_detail", pk=household.pk)


@module_permission_required('Clients', 'write')
def travel_group_create(request):
    if request.method == "POST":
        form = TravelGroupForm(request.POST)

        if form.is_valid():
            travel_group = form.save()
            messages.success(request, f"Travel group {travel_group.name} was created.")
            return redirect("clients:travel_group_detail", pk=travel_group.pk)
    else:
        form = TravelGroupForm()

    context = {
        "travel_group": None,
        "form": form,
        "form_title": "Add Travel Group",
        "form_subtitle": "Create a multi-family trip, reunion, wedding group, retreat, or related party.",
        "submit_label": "Create Travel Group",
    }

    return render(request, "clients/travel_group_form.html", context)


@module_permission_required('Clients', 'read')
def travel_group_detail(request, pk):
    travel_group = get_object_or_404(TravelGroup, pk=pk)

    memberships = travel_group.memberships.select_related(
        "household",
        "client",
    )
    member_form = TravelGroupMemberForm()
    member_form.fields['client'].widget.attrs['data-create-url'] = reverse('clients:travel_group_member_create_new_client', args=[travel_group.pk])
    member_form.fields['household'].widget.attrs['data-create-url'] = reverse('clients:travel_group_member_create_new_household', args=[travel_group.pk])

    context = {
        "travel_group": travel_group,
        "memberships": memberships,
        "member_form": member_form,
    }

    return render(request, "clients/travel_group_detail.html", context)


@module_permission_required('Clients', 'write')
def travel_group_update(request, pk):
    travel_group = get_object_or_404(TravelGroup, pk=pk)

    if request.method == "POST":
        form = TravelGroupForm(request.POST, instance=travel_group)

        if form.is_valid():
            travel_group = form.save()
            messages.success(request, f"Travel group {travel_group.name} was updated.")
            return redirect("clients:travel_group_detail", pk=travel_group.pk)
    else:
        form = TravelGroupForm(instance=travel_group)

    context = {
        "travel_group": travel_group,
        "form": form,
        "form_title": f"Edit {travel_group.name}",
        "form_subtitle": "Update travel group details, primary contact, and notes.",
        "submit_label": "Save Travel Group",
    }

    return render(request, "clients/travel_group_form.html", context)


@module_permission_required('Clients', 'write')
def travel_group_member_create(request, pk):
    travel_group = get_object_or_404(TravelGroup, pk=pk)

    if request.method == "POST":
        form = TravelGroupMemberForm(request.POST)

        if form.is_valid():
            membership = form.save(commit=False)
            membership.travel_group = travel_group
            membership.save()

            messages.success(request, "Travel group member was added.")
            return redirect("clients:travel_group_detail", pk=travel_group.pk)

        messages.error(request, "Please correct the travel group member form errors.")

    return redirect("clients:travel_group_detail", pk=travel_group.pk)


@module_permission_required('Clients', 'write')
def travel_group_member_create_new_client(request, pk):
    travel_group = get_object_or_404(TravelGroup, pk=pk)

    if request.method == "POST":
        form = ClientForm(request.POST)

        if form.is_valid():
            client = form.save()
            TravelGroupMember.objects.create(
                travel_group=travel_group,
                client=client,
                role=TravelGroupMember.Role.GUEST
            )
            messages.success(request, f"Client {client.display_name} was created and added to {travel_group.name}.")
            return redirect("clients:travel_group_detail", pk=travel_group.pk)
    else:
        form = ClientForm()

    context = {
        "form": form,
        "travel_group": travel_group,
        "form_title": "Add New Client to Travel Group",
        "form_subtitle": f"Create a new client profile and add them to {travel_group.name}.",
        "submit_label": "Create and Add Client",
    }

    return render(request, "clients/client_form.html", context)


@module_permission_required('Clients', 'write')
def travel_group_member_create_new_household(request, pk):
    travel_group = get_object_or_404(TravelGroup, pk=pk)

    if request.method == "POST":
        form = HouseholdForm(request.POST)

        if form.is_valid():
            household = form.save()
            TravelGroupMember.objects.create(
                travel_group=travel_group,
                household=household,
                role=TravelGroupMember.Role.FAMILY_UNIT
            )
            messages.success(request, f"Household {household.name} was created and added to {travel_group.name}.")
            return redirect("clients:travel_group_detail", pk=travel_group.pk)
    else:
        form = HouseholdForm()

    context = {
        "form": form,
        "travel_group": travel_group,
        "form_title": "Add New Household to Travel Group",
        "form_subtitle": f"Create a new household and add it to {travel_group.name}.",
        "submit_label": "Create and Add Household",
    }

    return render(request, "clients/household_form.html", context)


@module_permission_required('Clients', 'read')
def household_list(request):
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    households = Household.objects.select_related(
        "primary_contact",
        "billing_contact",
    ).all()

    if search_query:
        households = households.filter(
            Q(name__icontains=search_query)
            | Q(primary_contact__first_name__icontains=search_query)
            | Q(primary_contact__middle_name__icontains=search_query)
            | Q(primary_contact__last_name__icontains=search_query)
            | Q(billing_contact__first_name__icontains=search_query)
            | Q(billing_contact__middle_name__icontains=search_query)
            | Q(billing_contact__last_name__icontains=search_query)
            | Q(city__icontains=search_query)
            | Q(state__icontains=search_query)
        )

    if status_filter == "active":
        households = households.filter(is_active=True)
    elif status_filter == "inactive":
        households = households.filter(is_active=False)

    context = {
        "households": households,
        "search_query": search_query,
        "status_filter": status_filter,
        "total_households": Household.objects.count(),
        "active_households": Household.objects.filter(is_active=True).count(),
        "inactive_households": Household.objects.filter(is_active=False).count(),
        "search_result_count": households.count(),
    }

    return render(request, "clients/household_list.html", context)


@module_permission_required('Clients', 'read')
def travel_group_list(request):
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    group_type_filter = request.GET.get("group_type", "").strip()

    travel_groups = TravelGroup.objects.select_related("primary_contact").all()

    if search_query:
        travel_groups = travel_groups.filter(
            Q(name__icontains=search_query)
            | Q(primary_contact__first_name__icontains=search_query)
            | Q(primary_contact__middle_name__icontains=search_query)
            | Q(primary_contact__last_name__icontains=search_query)
            | Q(notes__icontains=search_query)
        )

    if status_filter == "active":
        travel_groups = travel_groups.filter(is_active=True)
    elif status_filter == "inactive":
        travel_groups = travel_groups.filter(is_active=False)

    if group_type_filter:
        travel_groups = travel_groups.filter(group_type=group_type_filter)

    context = {
        "travel_groups": travel_groups,
        "search_query": search_query,
        "status_filter": status_filter,
        "group_type_filter": group_type_filter,
        "total_travel_groups": TravelGroup.objects.count(),
        "active_travel_groups": TravelGroup.objects.filter(is_active=True).count(),
        "inactive_travel_groups": TravelGroup.objects.filter(is_active=False).count(),
        "search_result_count": travel_groups.count(),
        "group_type_choices": TravelGroup.GroupType.choices,
    }

    return render(request, "clients/travel_group_list.html", context)


@module_permission_required('Clients', 'read')
def contact_dashboard(request):
    context = {
        "total_clients": Client.objects.count(),
        "active_clients": Client.objects.filter(is_active=True).count(),
        "total_households": Household.objects.count(),
        "total_travel_groups": TravelGroup.objects.count(),
        "recent_notes": [],
    }

    return render(request, "clients/contact_dashboard.html", context)


@module_permission_required('Clients', 'delete')
def travel_group_member_delete(request, pk):
    membership = get_object_or_404(TravelGroupMember, pk=pk)
    travel_group = membership.travel_group

    if request.method == "POST":
        membership.delete()
        messages.success(request, "Travel group member was removed.")

    return redirect("clients:travel_group_detail", pk=travel_group.pk)


@module_permission_required('Clients', 'read')
def travel_group_detail_api(request, pk):
    travel_group = get_object_or_404(TravelGroup, pk=pk)
    households = []
    # Get all households that are members of this travel group
    for membership in travel_group.memberships.filter(household__isnull=False).select_related('household'):
        households.append({
            'id': membership.household.pk,
            'name': membership.household.name
        })
        
    data = {
        "id": travel_group.pk,
        "name": travel_group.name,
        "primary_contact_id": travel_group.primary_contact_id,
        "households": households,
    }
    return JsonResponse(data)


@module_permission_required('Clients', 'read')
def household_detail_api(request, pk):
    household = get_object_or_404(Household, pk=pk)
    data = {
        "id": household.pk,
        "name": household.name,
        "primary_contact_id": household.primary_contact_id,
    }
    return JsonResponse(data)


@module_permission_required('Clients', 'create')
def quick_add_client(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    name = request.POST.get('name', '').strip()
    travel_group_id = request.POST.get('travel_group_id', '').strip()
    household_id = request.POST.get('household_id', '').strip()
    
    if not name:
        return JsonResponse({'error': 'Name is required'}, status=400)
    
    parts = name.split(' ', 1)
    if len(parts) > 1:
        first_name, last_name = parts
    else:
        first_name = parts[0]
        last_name = "-"
        
    client = Client.objects.create(first_name=first_name, last_name=last_name)
    
    if travel_group_id:
        tg = TravelGroup.objects.filter(pk=travel_group_id).first()
        if tg:
            TravelGroupMember.objects.get_or_create(travel_group=tg, client=client)
            
    if household_id:
        hh = Household.objects.filter(pk=household_id).first()
        if hh:
            HouseholdMember.objects.get_or_create(household=hh, client=client)
            
    return JsonResponse({
        'id': client.pk,
        'name': client.full_name
    })


@module_permission_required('Clients', 'create')
def quick_add_household(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    name = request.POST.get('name', '').strip()
    travel_group_id = request.POST.get('travel_group_id', '').strip()
    
    if not name:
        return JsonResponse({'error': 'Name is required'}, status=400)
    
    household = Household.objects.create(name=name)
    
    if travel_group_id:
        tg = TravelGroup.objects.filter(pk=travel_group_id).first()
        if tg:
            TravelGroupMember.objects.get_or_create(travel_group=tg, household=household)
            
    return JsonResponse({
        'id': household.pk,
        'name': household.name
    })


@module_permission_required('Clients', 'create')
def quick_add_travel_group(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'Name is required'}, status=400)
    
    travel_group = TravelGroup.objects.create(name=name)
    return JsonResponse({
        'id': travel_group.pk,
        'name': travel_group.name
    })


@module_permission_required('Clients', 'create')
def quick_add_household_member(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    household = get_object_or_404(Household, pk=pk)
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'Name is required'}, status=400)
    
    parts = name.split(' ', 1)
    if len(parts) > 1:
        first_name, last_name = parts
    else:
        first_name = parts[0]
        last_name = "-"
        
    client = Client.objects.create(first_name=first_name, last_name=last_name)
    HouseholdMember.objects.create(household=household, client=client)
    
    return JsonResponse({
        'id': client.pk,
        'name': client.full_name
    })


@module_permission_required('Clients', 'create')
def quick_add_travel_group_member(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    travel_group = get_object_or_404(TravelGroup, pk=pk)
    name = request.POST.get('name', '').strip()
    member_type = request.POST.get('type', 'client').strip()
    household_id = request.POST.get('household_id', '').strip()
    
    if not name:
        return JsonResponse({'error': 'Name is required'}, status=400)
    
    if member_type == 'household':
        household = Household.objects.create(name=name)
        TravelGroupMember.objects.create(travel_group=travel_group, household=household)
        return JsonResponse({
            'id': household.pk,
            'name': household.name
        })
    else:
        parts = name.split(' ', 1)
        if len(parts) > 1:
            first_name, last_name = parts
        else:
            first_name = parts[0]
            last_name = "-"
            
        client = Client.objects.create(first_name=first_name, last_name=last_name)
        TravelGroupMember.objects.create(travel_group=travel_group, client=client)
        
        if household_id:
            household = get_object_or_404(Household, pk=household_id)
            HouseholdMember.objects.create(household=household, client=client)
        
        return JsonResponse({
            'id': client.pk,
            'name': client.full_name
        })


@module_permission_required('Clients', 'write')
def group_builder(request):
    """
    Unified interactive Group Builder:
    - Mode 'both': Create a Travel Group containing multiple Households & direct guests with drag-and-drop client assignment.
    - Mode 'household': Create a Household with drag-and-drop client assignment.
    - Mode 'travel_group': Create a Travel Group with drag-and-drop client & household assignment.
    """
    mode = request.GET.get("mode", request.POST.get("mode", "both")).strip()
    if mode not in ["both", "household", "travel_group"]:
        mode = "both"

    clients_param = request.GET.get("clients", "").strip()
    reservation_id_param = request.GET.get("reservation_id", "").strip()
    cabin_id_param = request.GET.get("cabin_id", "").strip()
    name_param = request.GET.get("name", "").strip()

    # Preselected client IDs from query
    preselected_client_ids = set()
    if clients_param:
        for cid in clients_param.split(","):
            try:
                preselected_client_ids.add(int(cid.strip()))
            except ValueError:
                pass

    reservation = None
    if reservation_id_param:
        try:
            reservation = Reservation.objects.prefetch_related("guests__client").filter(pk=int(reservation_id_param)).first()
            if reservation:
                for g in reservation.guests.all():
                    if g.client_id:
                        preselected_client_ids.add(g.client_id)
        except (ValueError, TypeError):
            pass

    cabin = None
    if cabin_id_param:
        try:
            cabin = Cabin.objects.filter(pk=int(cabin_id_param)).first()
            if cabin and not preselected_client_ids:
                for g in ReservationGuest.objects.filter(cabin=cabin).exclude(reservation__status=Reservation.ReservationStatus.CANCELLED):
                    if g.client_id:
                        preselected_client_ids.add(g.client_id)
        except (ValueError, TypeError):
            pass

    if request.method == "POST":
        is_json = request.content_type == "application/json" or request.headers.get("x-requested-with") == "XMLHttpRequest"

        post_data = request.POST
        if is_json and request.body:
            try:
                post_data = json.loads(request.body)
            except Exception:
                post_data = request.POST

        post_mode = post_data.get("mode", mode)
        reservation_id = post_data.get("reservation_id") or reservation_id_param
        cabin_id = post_data.get("cabin_id") or cabin_id_param

        def link_reservations(tg=None, created_hhs=None, single_hh=None, assigned_cids=None):
            affected = set()
            if reservation_id:
                try:
                    r = Reservation.objects.filter(pk=int(reservation_id)).first()
                    if r:
                        affected.add(r)
                except (ValueError, TypeError):
                    pass
            if cabin_id:
                try:
                    for r in Reservation.objects.filter(
                        Q(cabin_assignments__cabin_id=int(cabin_id)) | Q(guests__cabin_id=int(cabin_id))
                    ).exclude(status=Reservation.ReservationStatus.CANCELLED):
                        affected.add(r)
                except (ValueError, TypeError):
                    pass
            if assigned_cids:
                for r in Reservation.objects.filter(
                    Q(guests__client_id__in=assigned_cids) | Q(primary_contact_id__in=assigned_cids)
                ).exclude(status=Reservation.ReservationStatus.CANCELLED):
                    affected.add(r)

            for r in affected:
                changed = False
                if tg and r.travel_group_id != tg.id:
                    r.travel_group = tg
                    changed = True

                if single_hh:
                    if r.household_id != single_hh.id:
                        r.household = single_hh
                        changed = True
                elif created_hhs:
                    target_hh = None
                    if len(created_hhs) == 1:
                        target_hh = created_hhs[0]
                    else:
                        for hh in created_hhs:
                            if r.primary_contact_id and hh.memberships.filter(client_id=r.primary_contact_id).exists():
                                target_hh = hh
                                break
                        if not target_hh:
                            r_guest_client_ids = set(r.guests.values_list("client_id", flat=True))
                            best_match_count = 0
                            for hh in created_hhs:
                                match_count = hh.memberships.filter(client_id__in=r_guest_client_ids).count()
                                if match_count > best_match_count:
                                    best_match_count = match_count
                                    target_hh = hh
                    if target_hh and r.household_id != target_hh.id:
                        r.household = target_hh
                        changed = True

                if changed:
                    r.save()

        try:
            with transaction.atomic():
                if post_mode == "both":
                    tg_name = post_data.get("travel_group_name", "").strip()
                    group_type = post_data.get("group_type", TravelGroup.GroupType.MULTI_FAMILY_TRIP)
                    tg_notes = post_data.get("travel_group_notes", "").strip()
                    tg_years_raw = post_data.get("travel_group_years_return") or post_data.get("years_return")
                    tg_years = None
                    if tg_years_raw:
                        try:
                            tg_years = int(tg_years_raw)
                        except (ValueError, TypeError):
                            pass

                    if not tg_name:
                        tg_name = "New Travel Group"

                    travel_group = TravelGroup.objects.create(
                        name=tg_name,
                        group_type=group_type,
                        notes=tg_notes,
                        years_return=tg_years,
                    )

                    households_payload = post_data.get("households")
                    if isinstance(households_payload, str):
                        try:
                            households_payload = json.loads(households_payload)
                        except Exception:
                            households_payload = []
                    elif not households_payload:
                        households_payload = []

                    created_households = []
                    all_assigned_client_ids = set()

                    for idx, hh_item in enumerate(households_payload, start=1):
                        hh_name = hh_item.get("name", "").strip() or f"Household {idx}"
                        hh_notes = hh_item.get("notes", "").strip()
                        hh_years_raw = hh_item.get("years_return")
                        hh_years = None
                        if hh_years_raw:
                            try:
                                hh_years = int(hh_years_raw)
                            except (ValueError, TypeError):
                                pass
                        addr1 = hh_item.get("address_line_1", "").strip()
                        addr2 = hh_item.get("address_line_2", "").strip()
                        city = hh_item.get("city", "").strip()
                        state = hh_item.get("state", "").strip()
                        postal_code = hh_item.get("postal_code", "").strip()
                        country = hh_item.get("country", "United States").strip()
                        primary_contact_id = hh_item.get("primary_contact_id")
                        billing_contact_id = hh_item.get("billing_contact_id")

                        household = Household.objects.create(
                            name=hh_name,
                            address_line_1=addr1,
                            address_line_2=addr2,
                            city=city,
                            state=state,
                            postal_code=postal_code,
                            country=country,
                            notes=hh_notes,
                            years_return=hh_years,
                        )
                        created_households.append(household)

                        # Add household to travel group as family unit
                        TravelGroupMember.objects.create(
                            travel_group=travel_group,
                            household=household,
                            role=TravelGroupMember.Role.FAMILY_UNIT,
                        )

                        # Add members to household
                        hh_clients = hh_item.get("clients", [])
                        for client_item in hh_clients:
                            if isinstance(client_item, dict):
                                cid = client_item.get("id") or client_item.get("client_id")
                                rel = client_item.get("relationship", HouseholdMember.Relationship.UNKNOWN)
                            else:
                                cid = client_item
                                rel = HouseholdMember.Relationship.UNKNOWN

                            if not cid:
                                continue
                            try:
                                cid_int = int(cid)
                                is_prim = (str(cid_int) == str(primary_contact_id)) if primary_contact_id else False
                                is_bill = (str(cid_int) == str(billing_contact_id)) if billing_contact_id else False

                                HouseholdMember.objects.create(
                                    household=household,
                                    client_id=cid_int,
                                    relationship=rel,
                                    is_primary_contact=is_prim,
                                    is_billing_contact=is_bill,
                                )
                                all_assigned_client_ids.add(cid_int)

                                if is_prim or not household.primary_contact_id:
                                    household.primary_contact_id = cid_int
                                if is_bill:
                                    household.billing_contact_id = cid_int
                            except (ValueError, TypeError, Client.DoesNotExist):
                                continue

                        household.save()

                    # Direct travel group clients
                    direct_clients = post_data.get("direct_clients", [])
                    if isinstance(direct_clients, str):
                        try:
                            direct_clients = json.loads(direct_clients)
                        except Exception:
                            direct_clients = []

                    for dc in direct_clients:
                        if isinstance(dc, dict):
                            cid = dc.get("id") or dc.get("client_id")
                            role = dc.get("role", TravelGroupMember.Role.GUEST)
                        else:
                            cid = dc
                            role = TravelGroupMember.Role.GUEST
                        if not cid:
                            continue
                        try:
                            cid_int = int(cid)
                            TravelGroupMember.objects.create(
                                travel_group=travel_group,
                                client_id=cid_int,
                                role=role,
                            )
                            all_assigned_client_ids.add(cid_int)
                        except (ValueError, TypeError, Client.DoesNotExist):
                            continue

                    # Set primary contact for travel group
                    tg_primary_id = post_data.get("travel_group_primary_contact_id")
                    if tg_primary_id:
                        try:
                            travel_group.primary_contact_id = int(tg_primary_id)
                        except (ValueError, TypeError):
                            pass
                    elif created_households and created_households[0].primary_contact_id:
                        travel_group.primary_contact_id = created_households[0].primary_contact_id
                    elif all_assigned_client_ids:
                        travel_group.primary_contact_id = list(all_assigned_client_ids)[0]
                    travel_group.save()

                    # Link all affected reservations
                    link_reservations(tg=travel_group, created_hhs=created_households, assigned_cids=all_assigned_client_ids)

                    msg = f"Created Travel Group '{travel_group.name}' with {len(created_households)} household(s) and {len(all_assigned_client_ids)} guest(s)."
                    messages.success(request, msg)

                    if is_json:
                        return JsonResponse({
                            "success": True,
                            "redirect_url": reverse("clients:travel_group_detail", args=[travel_group.pk]),
                            "message": msg,
                        })
                    return redirect("clients:travel_group_detail", pk=travel_group.pk)

                elif post_mode == "household":
                    hh_name = post_data.get("household_name", "").strip() or "New Household"
                    addr1 = post_data.get("address_line_1", "").strip()
                    addr2 = post_data.get("address_line_2", "").strip()
                    city = post_data.get("city", "").strip()
                    state = post_data.get("state", "").strip()
                    postal_code = post_data.get("postal_code", "").strip()
                    country = post_data.get("country", "United States").strip()
                    notes = post_data.get("notes", "").strip()
                    hh_years_raw = post_data.get("household_years_return") or post_data.get("years_return")
                    hh_years = None
                    if hh_years_raw:
                        try:
                            hh_years = int(hh_years_raw)
                        except (ValueError, TypeError):
                            pass
                    primary_contact_id = post_data.get("primary_contact_id")
                    billing_contact_id = post_data.get("billing_contact_id")

                    household = Household.objects.create(
                        name=hh_name,
                        address_line_1=addr1,
                        address_line_2=addr2,
                        city=city,
                        state=state,
                        postal_code=postal_code,
                        country=country,
                        notes=notes,
                        years_return=hh_years,
                    )

                    clients_payload = post_data.get("clients", [])
                    if isinstance(clients_payload, str):
                        try:
                            clients_payload = json.loads(clients_payload)
                        except Exception:
                            clients_payload = []

                    all_assigned_client_ids = set()
                    for client_item in clients_payload:
                        if isinstance(client_item, dict):
                            cid = client_item.get("id") or client_item.get("client_id")
                            rel = client_item.get("relationship", HouseholdMember.Relationship.UNKNOWN)
                        else:
                            cid = client_item
                            rel = HouseholdMember.Relationship.UNKNOWN
                        if not cid:
                            continue
                        try:
                            cid_int = int(cid)
                            is_prim = (str(cid_int) == str(primary_contact_id)) if primary_contact_id else False
                            is_bill = (str(cid_int) == str(billing_contact_id)) if billing_contact_id else False

                            HouseholdMember.objects.create(
                                household=household,
                                client_id=cid_int,
                                relationship=rel,
                                is_primary_contact=is_prim,
                                is_billing_contact=is_bill,
                            )
                            all_assigned_client_ids.add(cid_int)
                            if is_prim or not household.primary_contact_id:
                                household.primary_contact_id = cid_int
                            if is_bill:
                                household.billing_contact_id = cid_int
                        except (ValueError, TypeError, Client.DoesNotExist):
                            continue

                    household.save()

                    # Link all affected reservations
                    link_reservations(single_hh=household, assigned_cids=all_assigned_client_ids)

                    msg = f"Created Household '{household.name}'."
                    messages.success(request, msg)

                    if is_json:
                        return JsonResponse({
                            "success": True,
                            "redirect_url": reverse("clients:household_detail", args=[household.pk]),
                            "message": msg,
                        })
                    return redirect("clients:household_detail", pk=household.pk)

                elif post_mode == "travel_group":
                    tg_name = post_data.get("travel_group_name", "").strip() or "New Travel Group"
                    group_type = post_data.get("group_type", TravelGroup.GroupType.MULTI_FAMILY_TRIP)
                    notes = post_data.get("notes", "").strip()
                    tg_years_raw = post_data.get("travel_group_years_return") or post_data.get("years_return")
                    tg_years = None
                    if tg_years_raw:
                        try:
                            tg_years = int(tg_years_raw)
                        except (ValueError, TypeError):
                            pass

                    travel_group = TravelGroup.objects.create(
                        name=tg_name,
                        group_type=group_type,
                        notes=notes,
                        years_return=tg_years,
                    )

                    clients_payload = post_data.get("clients", [])
                    if isinstance(clients_payload, str):
                        try:
                            clients_payload = json.loads(clients_payload)
                        except Exception:
                            clients_payload = []

                    all_assigned_client_ids = set()
                    for client_item in clients_payload:
                        if isinstance(client_item, dict):
                            cid = client_item.get("id") or client_item.get("client_id")
                            role = client_item.get("role", TravelGroupMember.Role.GUEST)
                        else:
                            cid = client_item
                            role = TravelGroupMember.Role.GUEST
                        if not cid:
                            continue
                        try:
                            cid_int = int(cid)
                            TravelGroupMember.objects.create(
                                travel_group=travel_group,
                                client_id=cid_int,
                                role=role,
                            )
                            all_assigned_client_ids.add(cid_int)
                            if not travel_group.primary_contact_id:
                                travel_group.primary_contact_id = cid_int
                        except (ValueError, TypeError):
                            continue

                    hh_ids = post_data.get("households", [])
                    if isinstance(hh_ids, str):
                        try:
                            hh_ids = json.loads(hh_ids)
                        except Exception:
                            hh_ids = []

                    for hid in hh_ids:
                        try:
                            hid_int = int(hid)
                            TravelGroupMember.objects.create(
                                travel_group=travel_group,
                                household_id=hid_int,
                                role=TravelGroupMember.Role.FAMILY_UNIT,
                            )
                        except (ValueError, TypeError):
                            continue

                    travel_group.save()

                    # Link all affected reservations
                    link_reservations(tg=travel_group, assigned_cids=all_assigned_client_ids)

                    msg = f"Created Travel Group '{travel_group.name}'."
                    messages.success(request, msg)

                    if is_json:
                        return JsonResponse({
                            "success": True,
                            "redirect_url": reverse("clients:travel_group_detail", args=[travel_group.pk]),
                            "message": msg,
                        })
                    return redirect("clients:travel_group_detail", pk=travel_group.pk)

        except Exception as e:
            if is_json:
                return JsonResponse({"error": str(e)}, status=400)
            messages.error(request, f"Error creating group: {str(e)}")

    # GET context
    all_clients = Client.objects.filter(is_active=True).prefetch_related(
        "household_memberships__household",
        "travel_group_memberships__travel_group",
    ).order_by("last_name", "first_name")

    all_households = Household.objects.filter(is_active=True).prefetch_related(
        "memberships__client"
    ).order_by("name")

    # Serialize clients for JavaScript drag-and-drop
    clients_json_data = []
    for c in all_clients:
        first_hh_membership = c.household_memberships.first()
        first_hh = first_hh_membership.household if first_hh_membership else None
        hh_names = [m.household.name for m in c.household_memberships.all() if m.household]
        tg_names = [m.travel_group.name for m in c.travel_group_memberships.all() if m.travel_group]
        clients_json_data.append({
            "id": c.id,
            "first_name": c.first_name,
            "last_name": c.last_name,
            "full_name": c.full_name,
            "display_name": c.display_name,
            "email": c.email,
            "phone": c.phone,
            "client_type": c.get_client_type_display(),
            "client_type_raw": c.client_type,
            "riding_level": c.get_riding_level_display(),
            "riding_level_raw": c.riding_level,
            "years_return": c.years_return,
            "years_display": c.years_display,
            "dietary_notes": c.dietary_notes,
            "medical_notes": c.medical_notes,
            "general_notes": c.general_notes,
            "address_line_1": first_hh.address_line_1 if first_hh else "",
            "address_line_2": first_hh.address_line_2 if first_hh else "",
            "city": first_hh.city if first_hh else "",
            "state": first_hh.state if first_hh else "",
            "postal_code": first_hh.postal_code if first_hh else "",
            "country": first_hh.country if first_hh else "United States",
            "household_id": first_hh.id if first_hh else None,
            "household_name": first_hh.name if first_hh else "",
            "households": hh_names,
            "household_display": ", ".join(hh_names) if hh_names else "",
            "travel_groups": tg_names,
            "is_preselected": c.id in preselected_client_ids,
        })

    households_json_data = []
    for h in all_households:
        member_names = [m.client.full_name for m in h.memberships.all() if m.client]
        households_json_data.append({
            "id": h.id,
            "name": h.name,
            "city": h.city,
            "state": h.state,
            "years_return": h.years_return,
            "years_display": h.years_display,
            "member_count": len(member_names),
            "members_summary": ", ".join(member_names),
        })

    group_type_choices = [
        {"value": choice[0], "label": choice[1]}
        for choice in TravelGroup.GroupType.choices
    ]

    relationship_choices = [
        {"value": choice[0], "label": choice[1]}
        for choice in HouseholdMember.Relationship.choices
    ]

    role_choices = [
        {"value": choice[0], "label": choice[1]}
        for choice in TravelGroupMember.Role.choices
    ]

    context = {
        "mode": mode,
        "clients_json": json.dumps(clients_json_data),
        "households_json": json.dumps(households_json_data),
        "group_type_choices": group_type_choices,
        "relationship_choices": relationship_choices,
        "role_choices": role_choices,
        "group_type_choices_json": json.dumps(group_type_choices),
        "relationship_choices_json": json.dumps(relationship_choices),
        "role_choices_json": json.dumps(role_choices),
        "preselected_client_ids": list(preselected_client_ids),
        "preselected_client_ids_json": json.dumps(list(preselected_client_ids)),
        "reservation": reservation,
        "cabin": cabin,
        "name_param": name_param,
        "total_clients_count": len(clients_json_data),
    }

    return render(request, "clients/group_builder.html", context)
