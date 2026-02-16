"""DSB Module Views (ADR-041 Phase 0)."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from dsb.services import get_dsb_kpis


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """DSB Dashboard — DSGVO compliance overview."""
    tenant_id = getattr(request, "tenant_id", None)
    if tenant_id is None:
        return render(request, "dsb/dashboard.html", {"kpis": None})

    kpis = get_dsb_kpis(tenant_id)
    return render(request, "dsb/dashboard.html", {"kpis": kpis})
