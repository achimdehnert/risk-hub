"""Document URLs."""

from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("", views.document_list, name="document_list"),
    path("upload/", views.document_upload, name="upload"),
    path("upload-bulk/", views.document_bulk_upload, name="bulk_upload"),
    path(
        "<int:document_id>/",
        views.document_detail,
        name="document_detail",
    ),
    path(
        "download/<int:version_id>/",
        views.document_download,
        name="download",
    ),
]
