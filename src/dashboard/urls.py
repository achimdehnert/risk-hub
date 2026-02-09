"""Dashboard URL routes."""

from django.urls import path

from dashboard.views import (
    DashboardActivityPartialView,
    DashboardKPIPartialView,
    DashboardView,
)

app_name = "dashboard"

urlpatterns = [
    path("", DashboardView.as_view(), name="home"),
    path(
        "partials/kpis/",
        DashboardKPIPartialView.as_view(),
        name="kpi-partial",
    ),
    path(
        "partials/activity/",
        DashboardActivityPartialView.as_view(),
        name="activity-partial",
    ),
]
