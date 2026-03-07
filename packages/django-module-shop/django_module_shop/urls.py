"""URL patterns for django-module-shop.

Include in your project::

    path("billing/modules/", include("django_module_shop.urls")),
"""

from django.urls import path

from .views import ModuleApplyView, ModuleConfiguratorView, ModuleStatusView, ModuleToggleView

app_name = "module_shop"

urlpatterns = [
    path("", ModuleConfiguratorView.as_view(), name="configurator"),
    path("toggle/", ModuleToggleView.as_view(), name="toggle"),
    path("apply/", ModuleApplyView.as_view(), name="apply"),
    path("status/", ModuleStatusView.as_view(), name="status"),
]
