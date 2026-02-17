"""URL configuration f\u00fcr DSB Module (ADR-041 Phase 0+1)."""

from django.urls import path

from dsb import views

app_name = "dsb"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # Mandate CRUD
    path("mandate/", views.mandate_list, name="mandate-list"),
    path("mandate/create/", views.mandate_create, name="mandate-create"),
    path("mandate/<uuid:pk>/edit/", views.mandate_edit, name="mandate-edit"),
    path("mandate/<uuid:pk>/delete/", views.mandate_delete, name="mandate-delete"),
    # VVT (Processing Activities)
    path("vvt/", views.vvt_list, name="vvt-list"),
    path("vvt/create/", views.vvt_create, name="vvt-create"),
    path("vvt/<uuid:pk>/", views.vvt_detail, name="vvt-detail"),
    path("vvt/<uuid:pk>/edit/", views.vvt_edit, name="vvt-edit"),
    # TOM (Technical & Organizational Measures)
    path("tom/", views.tom_list, name="tom-list"),
    path("tom/tech/create/", views.tom_tech_create, name="tom-tech-create"),
    path("tom/tech/<uuid:pk>/edit/", views.tom_tech_edit, name="tom-tech-edit"),
    path("tom/org/create/", views.tom_org_create, name="tom-org-create"),
    path("tom/org/<uuid:pk>/edit/", views.tom_org_edit, name="tom-org-edit"),
    # AVV (Data Processing Agreements)
    path("avv/", views.dpa_list, name="dpa-list"),
    path("avv/create/", views.dpa_create, name="dpa-create"),
    path("avv/<uuid:pk>/edit/", views.dpa_edit, name="dpa-edit"),
    # Read-only lists
    path("audits/", views.audit_list, name="audit-list"),
    path("deletions/", views.deletion_list, name="deletion-list"),
    path("breaches/", views.breach_list, name="breach-list"),
]
