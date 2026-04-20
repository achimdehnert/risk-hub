"""Risk assessment URLs (UC-008)."""

from django.urls import path

from . import views

app_name = "risk"

urlpatterns = [
    # Dashboard
    path("", views.risk_dashboard, name="dashboard"),
    # Assessment CRUD
    path("assessments/", views.assessment_list, name="assessment_list"),
    path("assessments/neu/", views.assessment_create, name="assessment_create"),
    path("assessments/<int:assessment_id>/", views.assessment_detail, name="assessment_detail"),
    path("assessments/<int:assessment_id>/edit/", views.assessment_edit, name="assessment_edit"),
    path(
        "assessments/<int:assessment_id>/approve/",
        views.assessment_approve,
        name="assessment_approve",
    ),
    path(
        "assessments/<int:assessment_id>/delete/", views.assessment_delete, name="assessment_delete"
    ),
    # Hazard CRUD
    path("assessments/<int:assessment_id>/hazards/neu/", views.hazard_create, name="hazard_create"),
    path(
        "assessments/<int:assessment_id>/hazards/<int:hazard_id>/edit/",
        views.hazard_edit,
        name="hazard_edit",
    ),
    path(
        "assessments/<int:assessment_id>/hazards/<int:hazard_id>/delete/",
        views.hazard_delete,
        name="hazard_delete",
    ),
    # Protective Measures (STOP)
    path(
        "assessments/<int:assessment_id>/massnahmen/neu/",
        views.measure_create,
        name="measure_create",
    ),
    path(
        "assessments/<int:assessment_id>/massnahmen/<int:measure_id>/edit/",
        views.measure_edit,
        name="measure_edit",
    ),
    path(
        "assessments/<int:assessment_id>/massnahmen/<int:measure_id>/complete/",
        views.measure_complete,
        name="measure_complete",
    ),
    path(
        "assessments/<int:assessment_id>/massnahmen/<int:measure_id>/delete/",
        views.measure_delete,
        name="measure_delete",
    ),
    # Substitution Check
    path(
        "assessments/<int:assessment_id>/substitution/neu/",
        views.substitution_create,
        name="substitution_create",
    ),
    path(
        "assessments/<int:assessment_id>/substitution/<int:check_id>/edit/",
        views.substitution_edit,
        name="substitution_edit",
    ),
    path(
        "assessments/<int:assessment_id>/substitution/<int:check_id>/delete/",
        views.substitution_delete,
        name="substitution_delete",
    ),
]
