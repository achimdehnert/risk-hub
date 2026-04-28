"""Project URL patterns (ADR-041)."""

from django.urls import path

from projects import views

app_name = "projects"

urlpatterns = [
    path(
        "",
        views.project_list,
        name="project-list",
    ),
    path(
        "new/",
        views.project_create,
        name="project-create",
    ),
    path(
        "<int:pk>/",
        views.project_detail,
        name="project-detail",
    ),
    path(
        "recommend-modules/",
        views.project_recommend_modules,
        name="recommend-modules",
    ),
    # Documents (Upload)
    path(
        "<int:pk>/upload/",
        views.document_upload,
        name="document-upload",
    ),
    path(
        "<int:pk>/docs/<int:doc_pk>/delete/",
        views.document_delete,
        name="document-delete",
    ),
    # Output Documents (Dokument erstellen)
    path(
        "<int:pk>/documents/new/",
        views.output_document_create,
        name="output-document-create",
    ),
    path(
        "<int:pk>/documents/<int:doc_pk>/",
        views.output_document_edit,
        name="output-document-edit",
    ),
    path(
        "<int:pk>/documents/<int:doc_pk>/sections/<int:sec_pk>/save/",
        views.section_save,
        name="section-save",
    ),
    path(
        "<int:pk>/documents/<int:doc_pk>/sections/<int:sec_pk>/delete/",
        views.section_delete,
        name="section-delete",
    ),
    path(
        "<int:pk>/documents/<int:doc_pk>/sections/<int:sec_pk>/llm-prefill/",
        views.section_llm_prefill,
        name="section-llm-prefill",
    ),
    path(
        "<int:pk>/documents/<int:doc_pk>/pdf/",
        views.output_document_pdf,
        name="output-document-pdf",
    ),
    path(
        "<int:pk>/documents/<int:doc_pk>/prefill-from-docs/",
        views.document_prefill_from_docs,
        name="document-prefill-from-docs",
    ),
]
