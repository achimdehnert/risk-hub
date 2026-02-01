# src/substances/html_urls.py
"""URL-Konfiguration für Substances HTML-Views."""

from django.urls import path

from . import template_views

app_name = "substances"

urlpatterns = [
    # Dashboard
    path("", template_views.SubstanceHomeView.as_view(), name="home"),

    # Substances CRUD
    path(
        "substances/",
        template_views.SubstanceListView.as_view(),
        name="list"
    ),
    path(
        "substances/new/",
        template_views.SubstanceCreateView.as_view(),
        name="create"
    ),
    path(
        "substances/<uuid:pk>/",
        template_views.SubstanceDetailView.as_view(),
        name="detail"
    ),
    path(
        "substances/<uuid:pk>/edit/",
        template_views.SubstanceEditView.as_view(),
        name="edit"
    ),

    # SDS Upload & Approval
    path(
        "substances/<uuid:substance_pk>/sds/upload/",
        template_views.SdsUploadView.as_view(),
        name="sds-upload"
    ),
    path(
        "sds/<uuid:pk>/approve/",
        template_views.SdsApproveView.as_view(),
        name="sds-approve"
    ),

    # Gefahrstoffverzeichnis
    path(
        "register/",
        template_views.HazardRegisterView.as_view(),
        name="hazard-register"
    ),

    # Parteien (Hersteller/Lieferanten)
    path(
        "parties/",
        template_views.PartyListView.as_view(),
        name="party-list"
    ),

    # HTMX Partials
    path(
        "search/",
        template_views.SubstanceSearchView.as_view(),
        name="search"
    ),
]
