from django.urls import path

from . import views

app_name = "horses"

urlpatterns = [
    path("", views.horse_list, name="horse_list"),
]