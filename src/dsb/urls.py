"""URL configuration f\u00fcr DSB Module (ADR-038 Phase 1)."""

from django.urls import path

from dsb import views, views_breach, views_deletion, views_documents

app_name = "dsb"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    # Mandate CRUD
    path("mandates/", views.mandate_list, name="mandate-list"),
    path("mandates/new/", views.mandate_create, name="mandate-create"),
    path(
        "mandates/<uuid:pk>/edit/",
        views.mandate_edit,
        name="mandate-edit",
    ),
    path(
        "mandates/<uuid:pk>/delete/",
        views.mandate_delete,
        name="mandate-delete",
    ),
    # VVT (Art. 30)
    path("vvt/", views.vvt_list, name="vvt-list"),
    path("vvt/new/", views.vvt_create, name="vvt-create"),
    path("vvt/<uuid:pk>/", views.vvt_detail, name="vvt-detail"),
    path("vvt/<uuid:pk>/edit/", views.vvt_edit, name="vvt-edit"),
    # TOM (Art. 32)
    path("tom/", views.tom_list, name="tom-list"),
    path("tom/new/", views.tom_create, name="tom-create"),
    path("tom/<uuid:pk>/edit/", views.tom_edit, name="tom-edit"),
    # AVV (Art. 28)
    path("avv/", views.dpa_list, name="dpa-list"),
    path("avv/new/", views.dpa_create, name="dpa-create"),
    path("avv/<uuid:pk>/", views.dpa_detail, name="dpa-detail"),
    path("avv/<uuid:pk>/edit/", views.dpa_edit, name="dpa-edit"),
    path("avv/import/", views.avv_import, name="avv-import"),
    # CSV Import
    path("import/", views.csv_import, name="csv-import"),
    # Audits
    path("audits/", views.audit_list, name="audit-list"),
    # Datenpannen-Workflow (Art. 33 DSGVO)
    path("breaches/", views_breach.breach_list, name="breach-list"),
    path("breaches/new/", views_breach.breach_create, name="breach-create"),
    path("breaches/<uuid:pk>/", views_breach.breach_detail, name="breach-detail"),
    path("breaches/<uuid:pk>/advance/", views_breach.breach_advance, name="breach-advance"),
    # Dokumente (PDF-Archiv)
    path("dokumente/", views_documents.document_list, name="document-list"),
    path("dokumente/upload/", views_documents.document_upload, name="document-upload"),
    path("dokumente/<uuid:pk>/download/", views_documents.document_download, name="document-download"),
    path("dokumente/<uuid:pk>/delete/", views_documents.document_delete, name="document-delete"),
    # Löschprotokolle (alt)
    path("deletions/", views.deletion_list, name="deletion-list"),
    # Löschungsworkflow (Art. 17 DSGVO)
    path("loeschantraege/", views_deletion.deletion_request_list, name="deletion-request-list"),
    path("loeschantraege/neu/", views_deletion.deletion_request_create, name="deletion-request-create"),
    path("loeschantraege/<uuid:pk>/", views_deletion.deletion_request_detail, name="deletion-request-detail"),
    path("loeschantraege/<uuid:pk>/advance/", views_deletion.deletion_request_advance, name="deletion-request-advance"),
]
