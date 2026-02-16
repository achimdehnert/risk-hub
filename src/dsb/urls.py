"""URL configuration für DSB Module (ADR-041 Phase 0+1)."""

from django.urls import path

from dsb import views

app_name = "dsb"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("vvt/", views.vvt_list, name="vvt-list"),
    path("tom/", views.tom_list, name="tom-list"),
    path("avv/", views.dpa_list, name="dpa-list"),
    path("audits/", views.audit_list, name="audit-list"),
    path("deletions/", views.deletion_list, name="deletion-list"),
    path("breaches/", views.breach_list, name="breach-list"),
]
