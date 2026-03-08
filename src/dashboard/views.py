"""Dashboard views — central compliance overview."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from common.tenant import get_active_modules
from dashboard.services import get_compliance_kpis, get_recent_activities


class DashboardView(LoginRequiredMixin, View):
    """Main compliance dashboard."""

    template_name = "dashboard/home.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        kpis = get_compliance_kpis(tenant_id)
        activities = get_recent_activities(tenant_id)

        return render(
            request,
            self.template_name,
            {
                "kpis": kpis,
                "activities": activities,
            },
        )


class DashboardKPIPartialView(LoginRequiredMixin, View):
    """HTMX partial: refreshable KPI cards."""

    template_name = "dashboard/partials/kpi_cards.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        kpis = get_compliance_kpis(tenant_id)
        return render(
            request,
            self.template_name,
            {
                "kpis": kpis,
                "active_modules": get_active_modules(request),
            },
        )


class DashboardActivityPartialView(LoginRequiredMixin, View):
    """HTMX partial: refreshable activity feed."""

    template_name = "dashboard/partials/activity_feed.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        activities = get_recent_activities(tenant_id)
        return render(
            request,
            self.template_name,
            {
                "activities": activities,
            },
        )
