"""Brandschutz URL configuration."""

from django.urls import path

from . import views

app_name = "brandschutz"

urlpatterns = [
    path("", views.ConceptListView.as_view(), name="concept-list"),
    path("new/", views.ConceptCreateView.as_view(), name="concept-create"),
    path(
        "<uuid:pk>/",
        views.ConceptDetailView.as_view(),
        name="concept-detail",
    ),
    path(
        "<uuid:pk>/edit/",
        views.ConceptEditView.as_view(),
        name="concept-edit",
    ),
    path(
        "<uuid:concept_pk>/sections/new/",
        views.SectionCreateView.as_view(),
        name="section-create",
    ),
    path(
        "<uuid:concept_pk>/documents/upload/",
        views.DocumentUploadView.as_view(),
        name="document-upload",
    ),
    path(
        "extinguishers/",
        views.ExtinguisherListView.as_view(),
        name="extinguisher-list",
    ),
    path(
        "escape-routes/",
        views.EscapeRouteListView.as_view(),
        name="escape-route-list",
    ),
    path(
        "measures/<uuid:pk>/update/",
        views.MeasureUpdateView.as_view(),
        name="measure-update",
    ),
    path(
        "concept-doc/<uuid:pk>/analyze/",
        views.ConceptDocAnalyzeView.as_view(),
        name="concept-doc-analyze",
    ),
    # Phase E: Template-Auswahl + Formular + KI-Vorausfüllung
    path(
        "<uuid:concept_pk>/templates/",
        views.TemplateSelectView.as_view(),
        name="template-select",
    ),
    path(
        "filled/<uuid:pk>/edit/",
        views.FilledTemplateEditView.as_view(),
        name="filled-template-edit",
    ),
    path(
        "filled/<uuid:pk>/llm-prefill/",
        views.FilledTemplateLLMPrefillView.as_view(),
        name="filled-template-llm-prefill",
    ),
    path(
        "filled/<uuid:pk>/pdf/",
        views.FilledTemplatePDFView.as_view(),
        name="filled-template-pdf",
    ),
]
