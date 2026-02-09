"""Audit log URL routes."""

from django.urls import path

from audit.views import AuditLogCsvExportView, AuditLogView

app_name = "audit"

urlpatterns = [
    path("", AuditLogView.as_view(), name="log"),
    path(
        "export/csv/",
        AuditLogCsvExportView.as_view(),
        name="export-csv",
    ),
]
