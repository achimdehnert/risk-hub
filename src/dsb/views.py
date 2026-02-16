"""DSB Module Views (ADR-041 Phase 0+1)."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from dsb.services import get_dsb_kpis


def _tenant_id(request: HttpRequest):
    """Extract tenant_id or None."""
    return getattr(request, "tenant_id", None)


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """DSB Dashboard — DSGVO compliance overview."""
    tid = _tenant_id(request)
    if tid is None:
        return render(request, "dsb/dashboard.html", {"kpis": None})

    kpis = get_dsb_kpis(tid)
    return render(request, "dsb/dashboard.html", {"kpis": kpis})


@login_required
def vvt_list(request: HttpRequest) -> HttpResponse:
    """VVT list — Art. 30 processing activities."""
    from dsb.models import ProcessingActivity

    tid = _tenant_id(request)
    qs = ProcessingActivity.objects.filter(
        tenant_id=tid,
    ).select_related("mandate").order_by("mandate", "number")
    high_risk = qs.filter(
        risk_level__in=["high", "very_high"],
    ).count()
    return render(request, "dsb/vvt_list.html", {
        "rows": qs[:200],
        "high_risk_count": high_risk,
    })


@login_required
def tom_list(request: HttpRequest) -> HttpResponse:
    """TOM list — Art. 32 technical & organizational measures."""
    from dsb.models import OrganizationalMeasure, TechnicalMeasure
    from dsb.models.choices import MeasureStatus

    tid = _tenant_id(request)
    tech = TechnicalMeasure.objects.filter(
        tenant_id=tid,
    ).select_related("category").order_by("name")
    org = OrganizationalMeasure.objects.filter(
        tenant_id=tid,
    ).select_related("category").order_by("name")
    planned = (
        tech.filter(status=MeasureStatus.PLANNED).count()
        + org.filter(status=MeasureStatus.PLANNED).count()
    )
    return render(request, "dsb/tom_list.html", {
        "tech_rows": tech[:200],
        "org_rows": org[:200],
        "planned_count": planned,
    })


@login_required
def dpa_list(request: HttpRequest) -> HttpResponse:
    """AVV list — Art. 28 data processing agreements."""
    from dsb.models import DataProcessingAgreement

    tid = _tenant_id(request)
    qs = DataProcessingAgreement.objects.filter(
        tenant_id=tid,
    ).select_related("mandate").order_by("-effective_date")
    expired = qs.filter(status="expired").count()
    return render(request, "dsb/dpa_list.html", {
        "rows": qs[:200],
        "expired_count": expired,
    })


@login_required
def audit_list(request: HttpRequest) -> HttpResponse:
    """Audit list — privacy audits."""
    from dsb.models import PrivacyAudit
    from dsb.models.audit import AuditFinding
    from dsb.models.choices import SeverityLevel

    tid = _tenant_id(request)
    qs = PrivacyAudit.objects.filter(
        tenant_id=tid,
    ).select_related("mandate").prefetch_related("findings")
    critical = AuditFinding.objects.filter(
        tenant_id=tid,
        severity=SeverityLevel.CRITICAL,
        status="open",
    ).count()
    return render(request, "dsb/audit_list.html", {
        "rows": qs[:200],
        "critical_findings": critical,
    })


@login_required
def deletion_list(request: HttpRequest) -> HttpResponse:
    """Deletion log list — Art. 17."""
    from dsb.models import DeletionLog

    tid = _tenant_id(request)
    qs = DeletionLog.objects.filter(
        tenant_id=tid,
    ).select_related("mandate", "data_category")
    pending = qs.filter(executed_at__isnull=True).count()
    return render(request, "dsb/deletion_list.html", {
        "rows": qs[:200],
        "pending_count": pending,
    })


@login_required
def breach_list(request: HttpRequest) -> HttpResponse:
    """Breach list — Art. 33 data breaches."""
    from dsb.models import Breach

    tid = _tenant_id(request)
    qs = Breach.objects.filter(
        tenant_id=tid,
    ).select_related("mandate").order_by("-discovered_at")
    overdue = sum(1 for b in qs if b.is_overdue)
    return render(request, "dsb/breach_list.html", {
        "rows": qs[:200],
        "overdue_count": overdue,
    })
