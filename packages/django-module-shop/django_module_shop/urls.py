"""URL patterns for django-module-shop (ADR-137 Phase 3)."""

from django.urls import path

from . import views

app_name = "module_shop"

urlpatterns = [
    path(
        "",
        views.catalogue_view,
        name="catalogue",
    ),
    path(
        "<str:code>/",
        views.detail_view,
        name="detail",
    ),
    path(
        "<str:code>/activate/",
        views.activate_view,
        name="activate",
    ),
    path(
        "<str:code>/cancel/",
        views.cancel_view,
        name="cancel",
    ),
]
