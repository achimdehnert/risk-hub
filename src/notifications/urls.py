"""Notification URL routes."""

from django.urls import path

from notifications.views import (
    NotificationBadgeView,
    NotificationDropdownView,
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
)

app_name = "notifications"

urlpatterns = [
    path(
        "",
        NotificationListView.as_view(),
        name="list",
    ),
    path(
        "dropdown/",
        NotificationDropdownView.as_view(),
        name="dropdown",
    ),
    path(
        "badge/",
        NotificationBadgeView.as_view(),
        name="badge",
    ),
    path(
        "<uuid:pk>/read/",
        NotificationMarkReadView.as_view(),
        name="mark-read",
    ),
    path(
        "mark-all-read/",
        NotificationMarkAllReadView.as_view(),
        name="mark-all-read",
    ),
]
