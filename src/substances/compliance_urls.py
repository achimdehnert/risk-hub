"""URL-Konfiguration für Compliance Module (UC-005, UC-006, UC-007)."""

from django.urls import path

from . import compliance_views as views

app_name = "compliance"

urlpatterns = [
    # UC-005: SDS Change Log
    path("changelog/", views.changelog_list, name="changelog_list"),
    path("changelog/<int:pk>/", views.changelog_detail, name="changelog_detail"),
    # UC-006: Compliance Review
    path("reviews/", views.review_dashboard, name="review_dashboard"),
    path("reviews/liste/", views.review_list, name="review_list"),
    path("reviews/neu/<int:usage_id>/", views.review_create, name="review_create"),
    # UC-007: Kataster Revision
    path("revisionen/", views.revision_list, name="revision_list"),
    path("revisionen/neu/", views.revision_create, name="revision_create"),
    path("revisionen/<int:pk>/", views.revision_detail, name="revision_detail"),
    path("revisionen/<int:pk>/approve/", views.revision_approve, name="revision_approve"),
]
