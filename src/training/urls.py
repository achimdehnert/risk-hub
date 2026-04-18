# src/training/urls.py
"""URL-Konfiguration für Unterweisungen (UC-009)."""

from django.urls import path

from . import views

app_name = "training"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    # Topics CRUD
    path("themen/", views.topic_list, name="topic-list"),
    path("themen/neu/", views.topic_create, name="topic-create"),
    path("themen/<int:pk>/", views.topic_detail, name="topic-detail"),
    path("themen/<int:pk>/edit/", views.topic_edit, name="topic-edit"),
    # Sessions CRUD
    path("sitzungen/", views.session_list, name="session-list"),
    path("sitzungen/neu/", views.session_create, name="session-create"),
    path("sitzungen/<int:pk>/", views.session_detail, name="session-detail"),
    path("sitzungen/<int:pk>/edit/", views.session_edit, name="session-edit"),
    path("sitzungen/<int:pk>/complete/", views.session_complete, name="session-complete"),
    # Attendance
    path("sitzungen/<int:pk>/teilnahme/", views.attendance_manage, name="attendance-manage"),
]
