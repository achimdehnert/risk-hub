"""URL configuration for Risk-Hub."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from config.api import api
from config.views import home, tenant_login, tenant_pick, user_profile
from core.healthz import liveness, readiness

urlpatterns = [
    # Health checks (ADR-021: /livez/ liveness + /healthz/ readiness)
    path("livez/", liveness, name="liveness"),
    path("healthz/", readiness, name="readiness"),
    path("", home),
    path("dashboard/", include("dashboard.urls")),
    path("admin/", admin.site.urls),
    path("accounts/login/", tenant_login, name="login"),
    path("accounts/login/pick/<slug:slug>/", tenant_pick, name="tenant-pick"),
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
    path("tenants/", include("tenancy.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
