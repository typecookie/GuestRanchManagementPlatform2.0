from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def vehicle_list(request):
    return render(request, "vehicles/vehicle_list.html")
