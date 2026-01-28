"""Risk assessment URLs."""

from django.urls import path
from . import views

app_name = "risk"

urlpatterns = [
    path("assessments/", views.assessment_list, name="assessment_list"),
    path("assessments/<uuid:assessment_id>/", views.assessment_detail, name="assessment_detail"),
    path("assessments/<uuid:assessment_id>/approve/", views.assessment_approve, name="assessment_approve"),
]
