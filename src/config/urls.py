"""URL configuration for Risk-Hub."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from config.api import api
from config.views import (
    custom_403,
    custom_404,
    custom_500,
    home,
    register,
    tenant_login,
    tenant_pick,
    trial_request,
    user_profile,
)
from core.healthz import liveness, readiness

handler403 = custom_403
handler404 = custom_404
handler500 = custom_500

urlpatterns = [
    # Health checks (ADR-021: /livez/ liveness + /healthz/ + /readyz/ readiness)
    path("livez/", liveness, name="liveness"),
    path("healthz/", readiness, name="readiness"),
    path("readyz/", readiness, name="readyz"),
    path("", home),
    path("dashboard/", include("dashboard.urls")),
    path("admin/", admin.site.urls),
    path("accounts/login/", tenant_login, name="login"),
    path("accounts/register/", register, name="register"),
    path("trial-request/", trial_request, name="trial-request"),
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
    path("gbu/", include("gbu.urls")),
    path("tenants/", include("tenancy.urls")),
    path("billing/modules/", include("django_module_shop.urls")),
    path("brandschutz/", include("brandschutz.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
