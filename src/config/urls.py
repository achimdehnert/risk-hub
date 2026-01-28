"""URL configuration for Risk-Hub."""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("risk/", include("risk.urls")),
    path("documents/", include("documents.urls")),
    path("actions/", include("actions.urls")),
]
