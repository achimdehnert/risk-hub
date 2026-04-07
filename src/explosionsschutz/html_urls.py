# src/explosionsschutz/html_urls.py
"""
HTML-Template URLs für Explosionsschutz-Modul
"""

from django.urls import path
from django.views.generic import RedirectView

from . import doc_template_views
from .concept_template_views import (
    ExConceptDocAnalyzeView,
    ExDocumentUploadView,
    ExFilledTemplateEditView,
    ExFilledTemplateLLMPrefillView,
    ExFilledTemplatePDFView,
    ExTemplateSelectView,
)
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
    AreaIFCUploadView,
    AreaListView,
    ConceptCreateView,
    ConceptDetailView,
    ConceptDxfImportView,
    ConceptEditView,
    ConceptListView,
    ConceptValidateView,
    EquipmentCreateView,
    EquipmentDetailView,
    EquipmentListView,
    HomeView,
    HtmxAddDocumentView,
    HtmxAddMeasureView,
    HtmxAddZoneView,
    HtmxDeleteMeasureView,
    HtmxDeleteZoneView,
    HtmxIgnitionAssessmentView,
    HtmxZoneProposalView,
    InspectionCreateView,
    ToolsView,
    ZoneCalculateView,
)

app_name = "explosionsschutz"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    # Areas
    path("areas/", AreaListView.as_view(), name="area-list-html"),
    path(
        "areas/new/",
        RedirectView.as_view(pattern_name="explosionsschutz:area-create", permanent=True),
    ),
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
        "areas/<uuid:pk>/ifc/",
        AreaIFCUploadView.as_view(),
        name="area-ifc-upload",
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
    path("concepts/<uuid:pk>/edit/", ConceptEditView.as_view(), name="concept-edit"),
    path("concepts/<uuid:pk>/validate/", ConceptValidateView.as_view(), name="concept-validate"),
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
    # Inspection
    path(
        "equipment/<uuid:equipment_pk>/inspect/",
        InspectionCreateView.as_view(),
        name="inspection-create",
    ),
    # HTMX Partials
    path(
        "htmx/concepts/<uuid:concept_pk>/zones/add/",
        HtmxAddZoneView.as_view(),
        name="htmx-zone-add",
    ),
    path(
        "htmx/zones/<uuid:zone_pk>/delete/",
        HtmxDeleteZoneView.as_view(),
        name="htmx-zone-delete",
    ),
    path(
        "htmx/concepts/<uuid:concept_pk>/measures/add/",
        HtmxAddMeasureView.as_view(),
        name="htmx-measure-add",
    ),
    path(
        "htmx/measures/<uuid:measure_pk>/delete/",
        HtmxDeleteMeasureView.as_view(),
        name="htmx-measure-delete",
    ),
    path(
        "htmx/concepts/<uuid:concept_pk>/documents/add/",
        HtmxAddDocumentView.as_view(),
        name="htmx-document-add",
    ),
    path(
        "htmx/zones/<uuid:zone_pk>/ignition/",
        HtmxIgnitionAssessmentView.as_view(),
        name="htmx-ignition-assessment",
    ),
    path(
        "htmx/zone-proposal/",
        HtmxZoneProposalView.as_view(),
        name="htmx-zone-proposal",
    ),
    # ── Dokument-Templates (standalone) ─────────────────────────
    path(
        "doc-templates/",
        doc_template_views.template_list,
        name="ex-doc-templates",
    ),
    path(
        "doc-templates/create/",
        doc_template_views.template_create,
        name="ex-doc-template-create",
    ),
    path(
        "doc-templates/upload/",
        doc_template_views.template_upload,
        name="ex-doc-template-upload",
    ),
    path(
        "doc-templates/<int:pk>/edit/",
        doc_template_views.template_edit,
        name="ex-doc-template-edit",
    ),
    path(
        "doc-templates/<int:pk>/delete/",
        doc_template_views.template_delete,
        name="ex-doc-template-delete",
    ),
    path(
        "doc-templates/<int:template_pk>/new-instance/",
        doc_template_views.instance_create,
        name="ex-doc-instance-create",
    ),
    path(
        "doc-templates/<int:template_pk>/new-instance/<uuid:concept_pk>/",
        doc_template_views.instance_create_for_concept,
        name="ex-doc-instance-create-for-concept",
    ),
    path(
        "doc-instances/<int:pk>/edit/",
        doc_template_views.instance_edit,
        name="ex-doc-instance-edit",
    ),
    path(
        "doc-instances/<int:pk>/delete/",
        doc_template_views.instance_delete,
        name="ex-doc-instance-delete",
    ),
    path(
        "doc-instances/<int:pk>/llm-prefill/",
        doc_template_views.instance_llm_prefill,
        name="ex-doc-instance-llm-prefill",
    ),
    path(
        "doc-instances/<int:pk>/pdf/",
        doc_template_views.instance_pdf_export,
        name="ex-doc-instance-pdf",
    ),
    # ── Concept Templates (ADR-147) ─────────────────────────────
    path(
        "concepts/<uuid:concept_pk>/documents/upload/",
        ExDocumentUploadView.as_view(),
        name="ex-document-upload",
    ),
    path(
        "concept-doc/<uuid:pk>/analyze/",
        ExConceptDocAnalyzeView.as_view(),
        name="ex-concept-doc-analyze",
    ),
    path(
        "concepts/<uuid:concept_pk>/templates/",
        ExTemplateSelectView.as_view(),
        name="ex-template-select",
    ),
    path(
        "filled/<uuid:pk>/edit/",
        ExFilledTemplateEditView.as_view(),
        name="ex-filled-template-edit",
    ),
    path(
        "filled/<uuid:pk>/llm-prefill/",
        ExFilledTemplateLLMPrefillView.as_view(),
        name="ex-filled-template-llm-prefill",
    ),
    path(
        "filled/<uuid:pk>/pdf/",
        ExFilledTemplatePDFView.as_view(),
        name="ex-filled-template-pdf",
    ),
]
