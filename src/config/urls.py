"""URL configuration for Risk-Hub."""

from django.contrib import admin
from django.urls import include, path

from config.api import api
from config.views import home

urlpatterns = [
    path("", home),
    path("admin/", admin.site.urls),
    path("api/v1/", api.urls),
    path("risk/", include("risk.urls")),
    path("documents/", include("documents.urls")),
    path("actions/", include("actions.urls")),
    path("api/ex/", include("explosionsschutz.urls")),
    path("ex/", include("explosionsschutz.html_urls")),
    path("api/substances/", include("substances.urls")),
    path("substances/", include("substances.html_urls")),
]
