from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def horse_list(request):
    return render(request, "horses/horse_list.html")
