"""Project URL patterns (ADR-041)."""

from django.urls import path

from projects import views

app_name = "projects"

urlpatterns = [
    path(
        "",
        views.project_list,
        name="project-list",
    ),
    path(
        "new/",
        views.project_create,
        name="project-create",
    ),
    path(
        "<int:pk>/",
        views.project_detail,
        name="project-detail",
    ),
    path(
        "recommend-modules/",
        views.project_recommend_modules,
        name="recommend-modules",
    ),
]
