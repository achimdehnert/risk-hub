"""URL configuration for Risk-Hub."""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from config.api import api
from config.views import home, user_profile
from core.healthz import liveness, readiness

urlpatterns = [
    # Health checks (ADR-021: /livez/ liveness + /healthz/ readiness)
    path("livez/", liveness, name="liveness"),
    path("healthz/", readiness, name="healthz"),
    path("", home),
    path("dashboard/", include("dashboard.urls")),
    path("admin/", admin.site.urls),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
        ),
        name="login",
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path(
        "accounts/profile/",
        user_profile,
        name="user-profile",
    ),
    path("api/v1/", api.urls),
    path("risk/", include("risk.urls")),
    path("documents/", include("documents.urls")),
    path("actions/", include("actions.urls")),
    path("api/ex/", include("explosionsschutz.urls")),
    path("ex/", include("explosionsschutz.html_urls")),
    path("api/substances/", include("substances.urls")),
    path("substances/", include("substances.html_urls")),
    path(
        "notifications/",
        include("notifications.urls"),
    ),
    path("audit/", include("audit.urls")),
    path("dsb/", include("dsb.urls")),
]
