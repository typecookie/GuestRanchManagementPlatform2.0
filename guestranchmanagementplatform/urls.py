"""
URL configuration for guestranchmanagementplatform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("clients/", include("apps.clients.urls")),
    path("reservations/", include("apps.reservations.urls")),
    path("horses/", include("apps.horses.urls")),
    path("cabins/", include("apps.cabins.urls")),
    path("vehicles/", include("apps.vehicles.urls")),
    path("ranch/", include("apps.ranch.urls")),
    path("projects/", include("apps.projects.urls")),
    path("groups/", include("apps.groups.urls")),
    path("", include("apps.core.urls")),
]
