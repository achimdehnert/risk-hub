# src/explosionsschutz/html_urls.py
"""
HTML-Template URLs für Explosionsschutz-Modul
"""

from django.urls import path

from .template_views import (
    HomeView,
    AreaListView,
    AreaDetailView,
    ConceptListView,
    ConceptDetailView,
    EquipmentListView,
    EquipmentDetailView,
)

app_name = "ex"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("areas/", AreaListView.as_view(), name="area-list"),
    path("areas/<uuid:pk>/", AreaDetailView.as_view(), name="area-detail"),
    path("concepts/", ConceptListView.as_view(), name="concept-list"),
    path("concepts/<uuid:pk>/", ConceptDetailView.as_view(), name="concept-detail"),
    path("equipment/", EquipmentListView.as_view(), name="equipment-list"),
    path("equipment/<uuid:pk>/", EquipmentDetailView.as_view(), name="equipment-detail"),
]
