# src/global_sds/urls.py
"""URL-Konfiguration für Global SDS Library Frontend (ADR-012)."""

from django.urls import path

from global_sds import views, views_partials

app_name = "global_sds"

urlpatterns = [
    # Compliance Dashboard (§8)
    path(
        "",
        views.compliance_dashboard,
        name="dashboard",
    ),
    # SDS Upload (§5)
    path(
        "upload/",
        views.sds_upload,
        name="upload",
    ),
    # Revision Detail / Edit / Delete
    path(
        "revision/<int:pk>/",
        views.revision_detail,
        name="revision-detail",
    ),
    path(
        "revision/<int:pk>/edit/",
        views.revision_edit,
        name="revision-edit",
    ),
    path(
        "revision/<int:pk>/delete/",
        views.revision_delete,
        name="revision-delete",
    ),
    # HTMX Partials (§8.4)
    path(
        "compliance/diff/<int:pk>/",
        views.diff_panel,
        name="diff-panel",
    ),
    path(
        "compliance/adopt/<int:pk>/",
        views.adopt_update,
        name="adopt",
    ),
    path(
        "compliance/defer/<int:pk>/",
        views.defer_update,
        name="defer",
    ),
    # HTMX: SDS Datacard (ADR-017 §8)
    path(
        "datacard/<int:pk>/",
        views_partials.sds_datacard_partial,
        name="datacard",
    ),
]
