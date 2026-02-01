# src/explosionsschutz/html_urls.py
"""
HTML-Template URLs für Explosionsschutz-Modul
"""

from django.urls import path

from .template_views import (
    HomeView,
    AreaListView,
    AreaDetailView,
    AreaCreateView,
    AreaEditView,
    ConceptListView,
    ConceptDetailView,
    ConceptCreateView,
    EquipmentListView,
    EquipmentDetailView,
    EquipmentCreateView,
    ToolsView,
)

app_name = "explosionsschutz"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    # Areas
    path("areas/", AreaListView.as_view(), name="area-list-html"),
    path("areas/create/", AreaCreateView.as_view(), name="area-create"),
    path("areas/<uuid:pk>/", AreaDetailView.as_view(), name="area-detail-html"),
    path("areas/<uuid:pk>/edit/", AreaEditView.as_view(), name="area-edit"),
    # Concepts
    path("concepts/", ConceptListView.as_view(), name="concept-list-html"),
    path("concepts/new/", ConceptCreateView.as_view(), name="concept-new"),
    path("concepts/create/", ConceptCreateView.as_view(), name="concept-create"),
    path(
        "concepts/<uuid:pk>/",
        ConceptDetailView.as_view(),
        name="concept-detail-html"
    ),
    # Equipment
    path("equipment/", EquipmentListView.as_view(), name="equipment-list-html"),
    path("equipment/create/", EquipmentCreateView.as_view(), name="equipment-create"),
    path(
        "equipment/<uuid:pk>/",
        EquipmentDetailView.as_view(),
        name="equipment-detail-html"
    ),
    # Tools
    path("tools/", ToolsView.as_view(), name="tools"),
]
