from django.contrib import messages
from django.contrib.auth.decorators import login_required
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
