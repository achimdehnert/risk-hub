from django.urls import path
from . import views

app_name = "risk"

urlpatterns = [
    path("assessments/", views.assessment_list, name="assessment_list"),
]
