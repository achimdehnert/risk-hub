"""Dashboard views — central compliance overview."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from dashboard.services import get_compliance_kpis, get_recent_activities


def _get_active_modules(request: HttpRequest) -> set:
    """Resolve active module codes for the current user/tenant."""
    from common.context import get_context
    ctx = get_context()
    tenant_id = ctx.tenant_id
    if not tenant_id and request.user.is_authenticated:
        try:
            from django_tenancy.models import Membership
            m = (
                Membership.objects
                .filter(user=request.user)
                .select_related("organization")
                .order_by("created_at")
                .first()
            )
            if m and m.organization.is_active:
                tenant_id = m.organization.tenant_id
        except Exception:
            pass
    if not tenant_id:
        return set()
    try:
        from django_tenancy.module_models import ModuleSubscription
        return set(
            ModuleSubscription.objects.filter(
                tenant_id=tenant_id,
                status__in=["trial", "active"],
            ).values_list("module", flat=True)
        )
    except Exception:
        return set()


class DashboardView(LoginRequiredMixin, View):
    """Main compliance dashboard."""

    template_name = "dashboard/home.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        kpis = get_compliance_kpis(tenant_id)
        activities = get_recent_activities(tenant_id)

        return render(request, self.template_name, {
            "kpis": kpis,
            "activities": activities,
        })


class DashboardKPIPartialView(LoginRequiredMixin, View):
    """HTMX partial: refreshable KPI cards."""

    template_name = "dashboard/partials/kpi_cards.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        kpis = get_compliance_kpis(tenant_id)
        return render(request, self.template_name, {
            "kpis": kpis,
            "active_modules": _get_active_modules(request),
        })


class DashboardActivityPartialView(LoginRequiredMixin, View):
    """HTMX partial: refreshable activity feed."""

    template_name = "dashboard/partials/activity_feed.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        activities = get_recent_activities(tenant_id)
        return render(request, self.template_name, {
            "activities": activities,
        })
