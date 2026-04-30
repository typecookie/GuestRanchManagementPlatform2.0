from django.urls import path

from . import views

app_name = "cabins"

urlpatterns = [
    path("", views.cabin_list, name="cabin_list"),
    path("new/", views.cabin_create, name="cabin_create"),
    path("<int:pk>/", views.cabin_detail, name="cabin_detail"),
    path("<int:pk>/edit/", views.cabin_update, name="cabin_update"),
]