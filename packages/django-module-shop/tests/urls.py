"""Test URL configuration."""

from django.urls import include, path

urlpatterns = [
    path(
        "modules/",
        include(
            "django_module_shop.urls",
            namespace="module_shop",
        ),
    ),
]
