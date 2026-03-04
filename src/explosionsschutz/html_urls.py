# src/explosionsschutz/html_urls.py
"""
HTML-Template URLs für Explosionsschutz-Modul
"""

from django.urls import path

from .export_views import (
    ConceptExportDocxView,
    ConceptExportGAEBView,
    ConceptExportPdfView,
    ConceptPreviewView,
    ZoneMapView,
)
from .template_views import (
    AreaBrandschutzView,
    AreaCreateView,
    AreaDetailView,
    AreaDxfUploadView,
    AreaEditView,
    AreaListView,
    ConceptCreateView,
    ConceptDetailView,
    ConceptDxfImportView,
    ConceptListView,
    EquipmentCreateView,
    EquipmentDetailView,
    EquipmentListView,
    HomeView,
    ToolsView,
    ZoneCalculateView,
)

app_name = "explosionsschutz"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    # Areas
    path("areas/", AreaListView.as_view(), name="area-list-html"),
    path("areas/create/", AreaCreateView.as_view(), name="area-create"),
    path(
        "areas/<uuid:pk>/",
        AreaDetailView.as_view(),
        name="area-detail-html",
    ),
    path("areas/<uuid:pk>/edit/", AreaEditView.as_view(), name="area-edit"),
    path(
        "areas/<uuid:pk>/dxf/",
        AreaDxfUploadView.as_view(),
        name="area-dxf-upload",
    ),
    path(
        "areas/<uuid:pk>/brandschutz/",
        AreaBrandschutzView.as_view(),
        name="area-brandschutz",
    ),
    # Concepts
    path("concepts/", ConceptListView.as_view(), name="concept-list-html"),
    path("concepts/new/", ConceptCreateView.as_view(), name="concept-new"),
    path("concepts/create/", ConceptCreateView.as_view(), name="concept-create"),
    path("concepts/<uuid:pk>/", ConceptDetailView.as_view(), name="concept-detail-html"),
    # Equipment
    path("equipment/", EquipmentListView.as_view(), name="equipment-list-html"),
    path("equipment/create/", EquipmentCreateView.as_view(), name="equipment-create"),
    path("equipment/<uuid:pk>/", EquipmentDetailView.as_view(), name="equipment-detail-html"),
    # Zone Map
    path(
        "concepts/<uuid:pk>/zone-map/",
        ZoneMapView.as_view(),
        name="concept-zone-map",
    ),
    # Export
    path(
        "concepts/<uuid:pk>/preview/",
        ConceptPreviewView.as_view(),
        name="concept-preview",
    ),
    path(
        "concepts/<uuid:pk>/export/docx/",
        ConceptExportDocxView.as_view(),
        name="concept-export-docx",
    ),
    path(
        "concepts/<uuid:pk>/export/pdf/",
        ConceptExportPdfView.as_view(),
        name="concept-export-pdf",
    ),
    path(
        "concepts/<uuid:pk>/export/gaeb/",
        ConceptExportGAEBView.as_view(),
        name="concept-export-gaeb",
    ),
    # Zone Calculation (riskfw)
    path(
        "zones/<uuid:zone_pk>/calculate/",
        ZoneCalculateView.as_view(),
        name="zone-calculate",
    ),
    # DXF Import für Zonen
    path(
        "concepts/<uuid:pk>/dxf-import/",
        ConceptDxfImportView.as_view(),
        name="concept-dxf-import",
    ),
    # Tools
    path("tools/", ToolsView.as_view(), name="tools"),
]
