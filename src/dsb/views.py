"""DSB Module Views (ADR-041 Phase 0+1)."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from dsb.forms import (
    DataProcessingAgreementForm,
    MandateForm,
    OrganizationalMeasureForm,
    ProcessingActivityForm,
    TechnicalMeasureForm,
)
from dsb.services import get_dsb_kpis


def _tenant_id(request: HttpRequest):
    """Extract tenant_id or None."""
    return getattr(request, "tenant_id", None)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """DSB Dashboard — DSGVO compliance overview."""
    tid = _tenant_id(request)
    if tid is None:
        return render(request, "dsb/dashboard.html", {"kpis": None})
    kpis = get_dsb_kpis(tid)
    return render(request, "dsb/dashboard.html", {"kpis": kpis})


# ---------------------------------------------------------------------------
# Mandate CRUD
# ---------------------------------------------------------------------------


@login_required
def mandate_list(request: HttpRequest) -> HttpResponse:
    """List all mandates for the tenant."""
    from dsb.models import Mandate

    tid = _tenant_id(request)
    qs = Mandate.objects.filter(tenant_id=tid).order_by("name")
    return render(request, "dsb/mandate_list.html", {"rows": qs})


@login_required
def mandate_create(request: HttpRequest) -> HttpResponse:
    """Create a new mandate."""
    tid = _tenant_id(request)
    if request.method == "POST":
        form = MandateForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.tenant_id = tid
            obj.save()
            return redirect("dsb:mandate-list")
    else:
        form = MandateForm()
    return render(request, "dsb/mandate_form.html", {"form": form, "title": "Neues Mandat"})


@login_required
def mandate_edit(request: HttpRequest, pk) -> HttpResponse:
    """Edit an existing mandate."""
    from dsb.models import Mandate

    tid = _tenant_id(request)
    obj = get_object_or_404(Mandate, pk=pk, tenant_id=tid)
    if request.method == "POST":
        form = MandateForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect("dsb:mandate-list")
    else:
        form = MandateForm(instance=obj)
    return render(request, "dsb/mandate_form.html", {"form": form, "title": f"Mandat: {obj.name}", "obj": obj})


@login_required
def mandate_delete(request: HttpRequest, pk) -> HttpResponse:
    """Delete a mandate (POST only)."""
    from dsb.models import Mandate

    tid = _tenant_id(request)
    obj = get_object_or_404(Mandate, pk=pk, tenant_id=tid)
    if request.method == "POST":
        obj.delete()
        return redirect("dsb:mandate-list")
    return render(request, "dsb/confirm_delete.html", {
        "obj": obj,
        "title": f"Mandat \u00ab{obj.name}\u00bb l\u00f6schen?",
        "cancel_url": "dsb:mandate-list",
    })


# ---------------------------------------------------------------------------
# VVT (Processing Activities)
# ---------------------------------------------------------------------------


@login_required
def vvt_list(request: HttpRequest) -> HttpResponse:
    """VVT list — Art. 30 processing activities."""
    from dsb.models import ProcessingActivity

    tid = _tenant_id(request)
    qs = ProcessingActivity.objects.filter(
        tenant_id=tid,
    ).select_related("mandate").order_by("mandate", "number")
    high_risk = qs.filter(risk_level__in=["high", "very_high"]).count()
    return render(request, "dsb/vvt_list.html", {
        "rows": qs[:200],
        "high_risk_count": high_risk,
    })


@login_required
def vvt_create(request: HttpRequest) -> HttpResponse:
    """Create a new processing activity."""
    tid = _tenant_id(request)
    if request.method == "POST":
        form = ProcessingActivityForm(request.POST, tenant_id=tid)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.tenant_id = tid
            obj.save()
            form.save_m2m()
            return redirect("dsb:vvt-list")
    else:
        form = ProcessingActivityForm(tenant_id=tid)
    return render(request, "dsb/vvt_form.html", {"form": form, "title": "Neue Verarbeitungst\u00e4tigkeit"})


@login_required
def vvt_edit(request: HttpRequest, pk) -> HttpResponse:
    """Edit an existing processing activity."""
    from dsb.models import ProcessingActivity

    tid = _tenant_id(request)
    obj = get_object_or_404(ProcessingActivity, pk=pk, tenant_id=tid)
    if request.method == "POST":
        form = ProcessingActivityForm(request.POST, instance=obj, tenant_id=tid)
        if form.is_valid():
            form.save()
            return redirect("dsb:vvt-list")
    else:
        form = ProcessingActivityForm(instance=obj, tenant_id=tid)
    return render(request, "dsb/vvt_form.html", {
        "form": form,
        "title": f"VVT: {obj.name}",
        "obj": obj,
    })


@login_required
def vvt_detail(request: HttpRequest, pk) -> HttpResponse:
    """Detail view for a processing activity."""
    from dsb.models import ProcessingActivity

    tid = _tenant_id(request)
    obj = get_object_or_404(
        ProcessingActivity.objects.select_related("mandate").prefetch_related(
            "purposes", "data_categories", "data_subjects", "recipients",
            "technical_measures", "organizational_measures",
            "third_country_transfers", "retention_rules",
        ),
        pk=pk,
        tenant_id=tid,
    )
    return render(request, "dsb/vvt_detail.html", {"obj": obj})


# ---------------------------------------------------------------------------
# TOM (Technical & Organizational Measures)
# ---------------------------------------------------------------------------


@login_required
def tom_list(request: HttpRequest) -> HttpResponse:
    """TOM list — Art. 32 technical & organizational measures."""
    from dsb.models import OrganizationalMeasure, TechnicalMeasure
    from dsb.models.choices import MeasureStatus

    tid = _tenant_id(request)
    tech = TechnicalMeasure.objects.filter(
        tenant_id=tid,
    ).select_related("category").order_by("title")
    org = OrganizationalMeasure.objects.filter(
        tenant_id=tid,
    ).select_related("category").order_by("title")
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
def tom_tech_create(request: HttpRequest) -> HttpResponse:
    """Create a new technical measure."""
    tid = _tenant_id(request)
    if request.method == "POST":
        form = TechnicalMeasureForm(request.POST, tenant_id=tid)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.tenant_id = tid
            obj.save()
            return redirect("dsb:tom-list")
    else:
        form = TechnicalMeasureForm(tenant_id=tid)
    return render(request, "dsb/tom_form.html", {
        "form": form,
        "title": "Neue technische Ma\u00dfnahme",
        "measure_type": "technical",
    })


@login_required
def tom_tech_edit(request: HttpRequest, pk) -> HttpResponse:
    """Edit an existing technical measure."""
    from dsb.models import TechnicalMeasure

    tid = _tenant_id(request)
    obj = get_object_or_404(TechnicalMeasure, pk=pk, tenant_id=tid)
    if request.method == "POST":
        form = TechnicalMeasureForm(request.POST, instance=obj, tenant_id=tid)
        if form.is_valid():
            form.save()
            return redirect("dsb:tom-list")
    else:
        form = TechnicalMeasureForm(instance=obj, tenant_id=tid)
    return render(request, "dsb/tom_form.html", {
        "form": form,
        "title": f"TOM: {obj.title}",
        "obj": obj,
        "measure_type": "technical",
    })


@login_required
def tom_org_create(request: HttpRequest) -> HttpResponse:
    """Create a new organizational measure."""
    tid = _tenant_id(request)
    if request.method == "POST":
        form = OrganizationalMeasureForm(request.POST, tenant_id=tid)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.tenant_id = tid
            obj.save()
            return redirect("dsb:tom-list")
    else:
        form = OrganizationalMeasureForm(tenant_id=tid)
    return render(request, "dsb/tom_form.html", {
        "form": form,
        "title": "Neue organisatorische Ma\u00dfnahme",
        "measure_type": "organizational",
    })


@login_required
def tom_org_edit(request: HttpRequest, pk) -> HttpResponse:
    """Edit an existing organizational measure."""
    from dsb.models import OrganizationalMeasure

    tid = _tenant_id(request)
    obj = get_object_or_404(OrganizationalMeasure, pk=pk, tenant_id=tid)
    if request.method == "POST":
        form = OrganizationalMeasureForm(request.POST, instance=obj, tenant_id=tid)
        if form.is_valid():
            form.save()
            return redirect("dsb:tom-list")
    else:
        form = OrganizationalMeasureForm(instance=obj, tenant_id=tid)
    return render(request, "dsb/tom_form.html", {
        "form": form,
        "title": f"TOM: {obj.title}",
        "obj": obj,
        "measure_type": "organizational",
    })


# ---------------------------------------------------------------------------
# AVV (Data Processing Agreements)
# ---------------------------------------------------------------------------


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
def dpa_create(request: HttpRequest) -> HttpResponse:
    """Create a new data processing agreement."""
    tid = _tenant_id(request)
    if request.method == "POST":
        form = DataProcessingAgreementForm(request.POST, tenant_id=tid)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.tenant_id = tid
            obj.save()
            return redirect("dsb:dpa-list")
    else:
        form = DataProcessingAgreementForm(tenant_id=tid)
    return render(request, "dsb/dpa_form.html", {"form": form, "title": "Neuer AVV"})


@login_required
def dpa_edit(request: HttpRequest, pk) -> HttpResponse:
    """Edit an existing data processing agreement."""
    from dsb.models import DataProcessingAgreement

    tid = _tenant_id(request)
    obj = get_object_or_404(DataProcessingAgreement, pk=pk, tenant_id=tid)
    if request.method == "POST":
        form = DataProcessingAgreementForm(request.POST, instance=obj, tenant_id=tid)
        if form.is_valid():
            form.save()
            return redirect("dsb:dpa-list")
    else:
        form = DataProcessingAgreementForm(instance=obj, tenant_id=tid)
    return render(request, "dsb/dpa_form.html", {
        "form": form,
        "title": f"AVV: {obj.partner_name}",
        "obj": obj,
    })


# ---------------------------------------------------------------------------
# Audit List (read-only for now)
# ---------------------------------------------------------------------------


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
