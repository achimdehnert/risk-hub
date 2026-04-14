# src/substances/html_urls.py
"""URL-Konfiguration für Substances HTML-Views."""

from django.urls import path

from . import template_views

app_name = "substances"

urlpatterns = [
    # Dashboard
    path("", template_views.SubstanceHomeView.as_view(), name="home"),
    # Substances CRUD
    path("substances/", template_views.SubstanceListView.as_view(), name="list"),
    path("substances/new/", template_views.SubstanceCreateView.as_view(), name="create"),
    path("substances/<int:pk>/", template_views.SubstanceDetailView.as_view(), name="detail"),
    path("substances/<int:pk>/edit/", template_views.SubstanceEditView.as_view(), name="edit"),
    # SDS Upload & Approval
    path(
        "substances/<int:substance_pk>/sds/upload/",
        template_views.SdsUploadView.as_view(),
        name="sds-upload",
    ),
    path("sds/<int:pk>/approve/", template_views.SdsApproveView.as_view(), name="sds-approve"),
    # Gefahrstoffverzeichnis
    path("register/", template_views.HazardRegisterView.as_view(), name="hazard-register"),
    # Parteien (Hersteller/Lieferanten)
    path("parties/", template_views.PartyListView.as_view(), name="party-list"),
    # HTMX Partials
    path("search/", template_views.SubstanceSearchView.as_view(), name="search"),
    # Import
    path("import/", template_views.SubstanceImportView.as_view(), name="import"),
    # Lookup (externe Datenbanken)
    path("lookup/", template_views.SubstanceLookupView.as_view(), name="lookup"),
]
