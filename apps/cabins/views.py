from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from apps.groups.decorators import module_permission_required

from .forms import CabinForm, CabinInventoryItemForm, CabinInventoryMaintenanceLogForm
from .models import Cabin, CabinInventoryItem, CabinInventoryMaintenanceLog


@module_permission_required('Cabins', 'read')
def cabin_list(request):
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    housekeeping_filter = request.GET.get("housekeeping_status", "").strip()

    cabins = Cabin.objects.all()

    if search_query:
        cabins = cabins.filter(
            Q(name__icontains=search_query)
            | Q(cabin_number__icontains=search_query)
            | Q(bed_configuration__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(notes__icontains=search_query)
        )

    if status_filter:
        cabins = cabins.filter(status=status_filter)

    if housekeeping_filter:
        cabins = cabins.filter(housekeeping_status=housekeeping_filter)

    context = {
        "cabins": cabins,
        "search_query": search_query,
        "status_filter": status_filter,
        "housekeeping_filter": housekeeping_filter,
        "total_cabins": Cabin.objects.count(),
        "active_cabins": Cabin.objects.filter(is_active=True).count(),
        "available_cabins": Cabin.objects.filter(status=Cabin.CabinStatus.AVAILABLE).count(),
        "maintenance_cabins": Cabin.objects.filter(status=Cabin.CabinStatus.MAINTENANCE).count(),
        "search_result_count": cabins.count(),
        "status_choices": Cabin.CabinStatus.choices,
        "housekeeping_choices": Cabin.HousekeepingStatus.choices,
    }

    return render(request, "cabins/cabin_list.html", context)


@module_permission_required('Cabins', 'read')
def cabin_detail(request, pk):
    cabin = get_object_or_404(Cabin, pk=pk)
    inventory_items = cabin.inventory_items.all().prefetch_related('maintenance_logs')
    projects = cabin.projects.all().select_related('project_lead')
    item_maintenance_logs = CabinInventoryMaintenanceLog.objects.filter(
        item__cabin=cabin
    ).select_related('item')[:20]

    context = {
        "cabin": cabin,
        "inventory_items": inventory_items,
        "projects": projects,
        "item_maintenance_logs": item_maintenance_logs,
        "total_inventory_items": inventory_items.count(),
        "items_needing_attention": inventory_items.filter(
            Q(status=CabinInventoryItem.Status.MAINTENANCE) | Q(status=CabinInventoryItem.Status.OUT_OF_SERVICE)
        ).count(),
        "active_projects_count": projects.exclude(status='finished').count(),
    }

    return render(request, "cabins/cabin_detail.html", context)


@module_permission_required('Cabins', 'write')
def cabin_create(request):
    if request.method == "POST":
        form = CabinForm(request.POST)

        if form.is_valid():
            cabin = form.save()
            messages.success(request, f"Cabin {cabin.name} was created.")
            return redirect("cabins:cabin_detail", pk=cabin.pk)
    else:
        form = CabinForm()

    context = {
        "form": form,
        "form_title": "Add Cabin",
        "form_subtitle": "Create a cabin record for lodging and reservations.",
        "submit_label": "Create Cabin",
    }

    return render(request, "cabins/cabin_form.html", context)


@module_permission_required('Cabins', 'write')
def cabin_update(request, pk):
    cabin = get_object_or_404(Cabin, pk=pk)

    if request.method == "POST":
        form = CabinForm(request.POST, instance=cabin)

        if form.is_valid():
            cabin = form.save()
            messages.success(request, f"Cabin {cabin.name} was updated.")
            return redirect("cabins:cabin_detail", pk=cabin.pk)
    else:
        form = CabinForm(instance=cabin)

    context = {
        "cabin": cabin,
        "form": form,
        "form_title": f"Edit {cabin.name}",
        "form_subtitle": "Update cabin details, capacity, housekeeping, and status.",
        "submit_label": "Save Cabin",
    }

    return render(request, "cabins/cabin_form.html", context)


# Cabin Inventory Views

@module_permission_required('Cabins', 'write')
def cabin_inventory_item_create(request, cabin_pk):
    cabin = get_object_or_404(Cabin, pk=cabin_pk)

    if request.method == "POST":
        form = CabinInventoryItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.cabin = cabin
            item.save()
            messages.success(request, f"Inventory item '{item.name}' added to {cabin.name}.")
            return redirect("cabins:cabin_inventory_item_detail", pk=item.pk)
    else:
        form = CabinInventoryItemForm()

    context = {
        "cabin": cabin,
        "form": form,
        "form_title": f"Add Inventory Item to {cabin.name}",
        "form_subtitle": "Track appliances (washing machines, fridge, AC), furniture, and equipment.",
        "submit_label": "Add Item",
    }
    return render(request, "cabins/cabin_inventory_item_form.html", context)


@module_permission_required('Cabins', 'read')
def cabin_inventory_item_detail(request, pk):
    item = get_object_or_404(CabinInventoryItem.objects.select_related('cabin'), pk=pk)
    maintenance_logs = item.maintenance_logs.all()
    projects = item.projects.all().select_related('project_lead')
    quick_add_form = CabinInventoryMaintenanceLogForm()

    context = {
        "item": item,
        "cabin": item.cabin,
        "maintenance_logs": maintenance_logs,
        "projects": projects,
        "quick_add_form": quick_add_form,
    }
    return render(request, "cabins/cabin_inventory_item_detail.html", context)


@module_permission_required('Cabins', 'write')
def cabin_inventory_item_update(request, pk):
    item = get_object_or_404(CabinInventoryItem.objects.select_related('cabin'), pk=pk)

    if request.method == "POST":
        form = CabinInventoryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"Inventory item '{item.name}' was updated.")
            return redirect("cabins:cabin_inventory_item_detail", pk=item.pk)
    else:
        form = CabinInventoryItemForm(instance=item)

    context = {
        "cabin": item.cabin,
        "item": item,
        "form": form,
        "form_title": f"Edit {item.name}",
        "form_subtitle": f"Update specs, warranty, condition, and status for {item.name}.",
        "submit_label": "Save Changes",
    }
    return render(request, "cabins/cabin_inventory_item_form.html", context)


@module_permission_required('Cabins', 'delete')
def cabin_inventory_item_delete(request, pk):
    item = get_object_or_404(CabinInventoryItem.objects.select_related('cabin'), pk=pk)
    cabin_pk = item.cabin.pk
    item_name = item.name

    if request.method == "POST":
        item.delete()
        messages.success(request, f"Inventory item '{item_name}' was removed.")
        return redirect("cabins:cabin_detail", pk=cabin_pk)

    context = {
        "item": item,
        "cabin": item.cabin,
    }
    return render(request, "cabins/cabin_inventory_item_confirm_delete.html", context)


# Cabin Inventory Item Maintenance Log Views

@module_permission_required('Cabins', 'write')
def cabin_item_maintenance_log_create(request, item_pk):
    item = get_object_or_404(CabinInventoryItem.objects.select_related('cabin'), pk=item_pk)

    if request.method == "POST":
        form = CabinInventoryMaintenanceLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.item = item
            log.save()

            # Update item status if appropriate
            if log.status_update == CabinInventoryMaintenanceLog.StatusUpdate.OPERATIONAL:
                if item.status in [CabinInventoryItem.Status.MAINTENANCE, CabinInventoryItem.Status.OUT_OF_SERVICE]:
                    item.status = CabinInventoryItem.Status.OPERATIONAL
                    item.save(update_fields=['status'])
            elif log.status_update == CabinInventoryMaintenanceLog.StatusUpdate.OUT_OF_SERVICE:
                item.status = CabinInventoryItem.Status.OUT_OF_SERVICE
                item.save(update_fields=['status'])
            elif log.status_update == CabinInventoryMaintenanceLog.StatusUpdate.NEEDS_FOLLOW_UP:
                item.status = CabinInventoryItem.Status.MAINTENANCE
                item.save(update_fields=['status'])

            messages.success(request, f"Maintenance log added for {item.name}.")
            return redirect("cabins:cabin_inventory_item_detail", pk=item.pk)
    else:
        form = CabinInventoryMaintenanceLogForm()

    context = {
        "item": item,
        "cabin": item.cabin,
        "form": form,
        "form_title": f"Log Maintenance: {item.name}",
        "form_subtitle": f"Record repairs or routine servicing for {item.name} in {item.cabin.name}.",
        "submit_label": "Save Maintenance Record",
    }
    return render(request, "cabins/cabin_item_maintenance_log_form.html", context)


@module_permission_required('Cabins', 'write')
def cabin_item_maintenance_log_update(request, pk):
    log = get_object_or_404(CabinInventoryMaintenanceLog.objects.select_related('item__cabin'), pk=pk)
    item = log.item

    if request.method == "POST":
        form = CabinInventoryMaintenanceLogForm(request.POST, instance=log)
        if form.is_valid():
            form.save()
            messages.success(request, "Maintenance log updated.")
            return redirect("cabins:cabin_inventory_item_detail", pk=item.pk)
    else:
        form = CabinInventoryMaintenanceLogForm(instance=log)

    context = {
        "log": log,
        "item": item,
        "cabin": item.cabin,
        "form": form,
        "form_title": f"Edit Maintenance Record: {item.name}",
        "form_subtitle": f"Record date: {log.date}",
        "submit_label": "Save Changes",
    }
    return render(request, "cabins/cabin_item_maintenance_log_form.html", context)


@module_permission_required('Cabins', 'delete')
def cabin_item_maintenance_log_delete(request, pk):
    log = get_object_or_404(CabinInventoryMaintenanceLog.objects.select_related('item__cabin'), pk=pk)
    item_pk = log.item.pk

    if request.method == "POST":
        log.delete()
        messages.success(request, "Maintenance record deleted.")
        return redirect("cabins:cabin_inventory_item_detail", pk=item_pk)

    context = {
        "log": log,
        "item": log.item,
        "cabin": log.item.cabin,
    }
    return render(request, "cabins/cabin_item_maintenance_log_confirm_delete.html", context)
