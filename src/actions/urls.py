"""Action URLs (UC-Q06: Maßnahmen-Tracking)."""

from django.urls import path

from . import views

app_name = "actions"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("liste/", views.action_list, name="action-list"),
    path("neu/", views.action_create, name="action-create"),
    path("<int:pk>/", views.action_detail, name="action-detail"),
    path("<int:pk>/edit/", views.action_edit, name="action-edit"),
    path("<int:pk>/complete/", views.action_complete, name="action-complete"),
]
