"""URL configuration für DSB Module (ADR-041 Phase 0)."""

from django.urls import path

from dsb import views

app_name = "dsb"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # Phase 1: CRUD views (pending)
    # path("vvt/", views.vvt_list, name="vvt-list"),
    # path("audits/", views.audit_list, name="audit-list"),
    # path("deletions/", views.deletion_list, name="deletion-list"),
    # path("breaches/", views.breach_list, name="breach-list"),
]
