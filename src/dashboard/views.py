"""Dashboard views — central compliance overview."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from dashboard.services import get_compliance_kpis, get_recent_activities


class DashboardView(View):
    """Main compliance dashboard."""

    template_name = "dashboard/home.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        if tenant_id is None:
            return render(request, "landing.html")

        kpis = get_compliance_kpis(tenant_id)
        activities = get_recent_activities(tenant_id)

        return render(request, self.template_name, {
            "kpis": kpis,
            "activities": activities,
        })


class DashboardKPIPartialView(View):
    """HTMX partial: refreshable KPI cards."""

    template_name = "dashboard/partials/kpi_cards.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        kpis = get_compliance_kpis(tenant_id)
        return render(request, self.template_name, {
            "kpis": kpis,
        })


class DashboardActivityPartialView(View):
    """HTMX partial: refreshable activity feed."""

    template_name = "dashboard/partials/activity_feed.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        activities = get_recent_activities(tenant_id)
        return render(request, self.template_name, {
            "activities": activities,
        })
