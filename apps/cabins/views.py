from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CabinForm
from .models import Cabin


@login_required
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


@login_required
def cabin_detail(request, pk):
    cabin = get_object_or_404(Cabin, pk=pk)

    context = {
        "cabin": cabin,
    }

    return render(request, "cabins/cabin_detail.html", context)


@login_required
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


@login_required
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
