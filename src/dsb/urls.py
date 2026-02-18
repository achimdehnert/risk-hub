"""URL configuration f\u00fcr DSB Module (ADR-038 Phase 1)."""

from django.urls import path

from dsb import views

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
    path("avv/<uuid:pk>/edit/", views.dpa_edit, name="dpa-edit"),
    # CSV Import
    path("import/", views.csv_import, name="csv-import"),
    # Audits + Deletion + Breach (list-only for now)
    path("audits/", views.audit_list, name="audit-list"),
    path("deletions/", views.deletion_list, name="deletion-list"),
    path("breaches/", views.breach_list, name="breach-list"),
]
