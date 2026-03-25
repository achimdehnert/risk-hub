"""Brandschutz URL configuration."""

from django.urls import path

from . import views

app_name = "brandschutz"

urlpatterns = [
    path("", views.ConceptListView.as_view(), name="concept-list"),
    path("new/", views.ConceptCreateView.as_view(), name="concept-create"),
    path(
        "<uuid:pk>/",
        views.ConceptDetailView.as_view(),
        name="concept-detail",
    ),
    path(
        "<uuid:pk>/edit/",
        views.ConceptEditView.as_view(),
        name="concept-edit",
    ),
    path(
        "<uuid:concept_pk>/sections/new/",
        views.SectionCreateView.as_view(),
        name="section-create",
    ),
    path(
        "extinguishers/",
        views.ExtinguisherListView.as_view(),
        name="extinguisher-list",
    ),
    path(
        "escape-routes/",
        views.EscapeRouteListView.as_view(),
        name="escape-route-list",
    ),
    path(
        "measures/<uuid:pk>/update/",
        views.MeasureUpdateView.as_view(),
        name="measure-update",
    ),
]
