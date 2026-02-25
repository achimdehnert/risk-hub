"""DSB Module Views (ADR-041 Phase 0+1)."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from django_tenancy.module_access import require_module
from dsb.services import get_dsb_kpis


def _tenant_id(request: HttpRequest):
    """Extract tenant_id — falls back to user membership for dev (no subdomain)."""
    tid = getattr(request, "tenant_id", None)
    if tid is not None:
        return tid
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        try:
            from django_tenancy.models import Membership
            m = (
                Membership.objects
                .filter(user=user)
                .select_related("organization")
                .order_by("created_at")
                .first()
            )
            if m and m.organization.is_active:
                return m.organization.tenant_id
        except Exception:
            pass
    return None


def _user_id(request: HttpRequest):
    """Extract user UUID or None."""
    u = getattr(request, "user", None)
    if u and hasattr(u, "pk"):
        return u.pk
    return None


@login_required
@require_module("dsb")
def dashboard(request: HttpRequest) -> HttpResponse:
    """DSB Dashboard — DSGVO compliance overview."""
    from dsb.models import Breach
    from dsb.models.deletion import DeletionRequest

    tid = _tenant_id(request)
    kpis = get_dsb_kpis(tid) if tid else None

    open_breaches = []
    open_deletions = []
    if tid:
        open_breaches = (
            Breach.objects.filter(tenant_id=tid)
            .exclude(workflow_status__in=["closed", "authority_closed"])
            .select_related("mandate")
            .order_by("discovered_at")[:10]
        )
        open_deletions = (
            DeletionRequest.objects.filter(tenant_id=tid)
            .exclude(status__in=["completed", "rejected"])
            .select_related("mandate")
            .order_by("created_at")[:10]
        )

    return render(request, "dsb/dashboard.html", {
        "kpis": kpis,
        "open_breaches": open_breaches,
        "open_deletions": open_deletions,
    })


@login_required
@require_module("dsb")
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
@require_module("dsb")
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
@require_module("dsb")
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
@require_module("dsb")
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
@require_module("dsb")
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
@require_module("dsb")
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


# -----------------------------------------------------------------------
# Mandate CRUD
# -----------------------------------------------------------------------


@login_required
def mandate_list(request: HttpRequest) -> HttpResponse:
    """Mandate list — betreute Unternehmen."""
    from dsb.models import Mandate

    tid = _tenant_id(request)
    qs = Mandate.objects.filter(tenant_id=tid).order_by("name")
    active = qs.filter(status="active").count()
    return render(request, "dsb/mandate_list.html", {
        "rows": qs[:200],
        "active_count": active,
    })


@login_required
def mandate_create(request: HttpRequest) -> HttpResponse:
    """Create a new Mandate."""
    from dsb.forms import MandateForm

    tid = _tenant_id(request)
    if request.method == "POST":
        form = MandateForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.tenant_id = tid
            obj.created_by_id = _user_id(request)
            obj.save()
            return redirect("dsb:mandate-list")
    else:
        form = MandateForm()
    return render(request, "dsb/mandate_form.html", {
        "form": form,
        "title": "Neues Mandat anlegen",
    })


@login_required
def mandate_edit(request: HttpRequest, pk) -> HttpResponse:
    """Edit an existing Mandate."""
    from dsb.forms import MandateForm
    from dsb.models import Mandate

    tid = _tenant_id(request)
    obj = get_object_or_404(Mandate, pk=pk, tenant_id=tid)
    if request.method == "POST":
        form = MandateForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by_id = _user_id(request)
            obj.save()
            return redirect("dsb:mandate-list")
    else:
        form = MandateForm(instance=obj)
    return render(request, "dsb/mandate_form.html", {
        "form": form,
        "title": f"Mandat bearbeiten: {obj.name}",
        "object": obj,
    })


@login_required
def mandate_delete(request: HttpRequest, pk) -> HttpResponse:
    """Delete a Mandate (POST only)."""
    from dsb.models import Mandate

    tid = _tenant_id(request)
    obj = get_object_or_404(Mandate, pk=pk, tenant_id=tid)
    if request.method == "POST":
        obj.delete()
        return redirect("dsb:mandate-list")
    return render(request, "dsb/confirm_delete.html", {
        "object": obj,
        "cancel_url": "dsb:mandate-list",
        "type_label": "Mandat",
    })


# -----------------------------------------------------------------------
# VVT CRUD
# -----------------------------------------------------------------------


@login_required
@require_module("dsb")
def vvt_detail(request: HttpRequest, pk) -> HttpResponse:
    """VVT detail — single processing activity."""
    from dsb.models import ProcessingActivity

    tid = _tenant_id(request)
    obj = get_object_or_404(
        ProcessingActivity.objects.select_related("mandate"),
        pk=pk,
        tenant_id=tid,
    )
    return render(request, "dsb/vvt_detail.html", {"obj": obj})


@login_required
def vvt_create(request: HttpRequest) -> HttpResponse:
    """Create a new VVT entry."""
    from dsb.forms import ProcessingActivityForm

    tid = _tenant_id(request)
    if request.method == "POST":
        form = ProcessingActivityForm(request.POST, tenant_id=tid)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.tenant_id = tid
            obj.created_by_id = _user_id(request)
            obj.save()
            form.save_m2m()
            return redirect("dsb:vvt-list")
    else:
        form = ProcessingActivityForm(tenant_id=tid)
    return render(request, "dsb/vvt_form.html", {
        "form": form,
        "title": "Neue Verarbeitungstätigkeit",
    })


@login_required
def vvt_edit(request: HttpRequest, pk) -> HttpResponse:
    """Edit an existing VVT entry."""
    from dsb.forms import ProcessingActivityForm
    from dsb.models import ProcessingActivity

    tid = _tenant_id(request)
    obj = get_object_or_404(ProcessingActivity, pk=pk, tenant_id=tid)
    if request.method == "POST":
        form = ProcessingActivityForm(
            request.POST, instance=obj, tenant_id=tid,
        )
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by_id = _user_id(request)
            obj.save()
            form.save_m2m()
            return redirect("dsb:vvt-list")
    else:
        form = ProcessingActivityForm(instance=obj, tenant_id=tid)
    return render(request, "dsb/vvt_form.html", {
        "form": form,
        "title": f"VVT bearbeiten: {obj.name}",
        "object": obj,
    })


# -----------------------------------------------------------------------
# TOM CRUD
# -----------------------------------------------------------------------


@login_required
def tom_create(request: HttpRequest) -> HttpResponse:
    """Create a new TOM entry (tech or org)."""
    from dsb.forms import (
        OrganizationalMeasureForm,
        TechnicalMeasureForm,
    )

    tid = _tenant_id(request)
    measure_type = request.GET.get("type", "tech")
    FormClass = (
        TechnicalMeasureForm
        if measure_type == "tech"
        else OrganizationalMeasureForm
    )
    if request.method == "POST":
        form = FormClass(request.POST, tenant_id=tid)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.tenant_id = tid
            obj.created_by_id = _user_id(request)
            obj.save()
            return redirect("dsb:tom-list")
    else:
        form = FormClass(tenant_id=tid)
    label = (
        "Technische" if measure_type == "tech"
        else "Organisatorische"
    )
    return render(request, "dsb/tom_form.html", {
        "form": form,
        "title": f"Neue {label} Maßnahme",
        "measure_type": measure_type,
    })


@login_required
def tom_edit(request: HttpRequest, pk) -> HttpResponse:
    """Edit an existing TOM entry."""
    from dsb.forms import (
        OrganizationalMeasureForm,
        TechnicalMeasureForm,
    )
    from dsb.models import OrganizationalMeasure, TechnicalMeasure

    tid = _tenant_id(request)
    measure_type = request.GET.get("type", "tech")
    if measure_type == "tech":
        Model = TechnicalMeasure
        FormClass = TechnicalMeasureForm
    else:
        Model = OrganizationalMeasure
        FormClass = OrganizationalMeasureForm
    obj = get_object_or_404(Model, pk=pk, tenant_id=tid)
    if request.method == "POST":
        form = FormClass(
            request.POST, instance=obj, tenant_id=tid,
        )
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by_id = _user_id(request)
            obj.save()
            return redirect("dsb:tom-list")
    else:
        form = FormClass(instance=obj, tenant_id=tid)
    label = (
        "Technische" if measure_type == "tech"
        else "Organisatorische"
    )
    return render(request, "dsb/tom_form.html", {
        "form": form,
        "title": f"{label} Maßnahme bearbeiten: {obj.title}",
        "object": obj,
        "measure_type": measure_type,
    })


# -----------------------------------------------------------------------
# DPA (AVV) CRUD
# -----------------------------------------------------------------------


@login_required
def dpa_detail(request: HttpRequest, pk) -> HttpResponse:
    """Detail view for an AVV entry including linked documents."""
    from dsb.models import DataProcessingAgreement
    from dsb.models.document import DsbDocument

    tid = _tenant_id(request)
    obj = get_object_or_404(
        DataProcessingAgreement.objects.select_related("mandate")
        .prefetch_related("data_categories", "data_subjects", "processing_activities"),
        pk=pk, tenant_id=tid,
    )
    docs = DsbDocument.objects.filter(tenant_id=tid, ref_type="dpa", ref_id=obj.pk)
    return render(request, "dsb/dpa_detail.html", {
        "obj": obj,
        "docs": docs,
    })


@login_required
def dpa_create(request: HttpRequest) -> HttpResponse:
    """Create a new AVV entry."""
    from dsb.forms import DataProcessingAgreementForm

    tid = _tenant_id(request)
    if request.method == "POST":
        form = DataProcessingAgreementForm(
            request.POST, tenant_id=tid,
        )
        if form.is_valid():
            obj = form.save(commit=False)
            obj.tenant_id = tid
            obj.created_by_id = _user_id(request)
            obj.save()
            return redirect("dsb:dpa-list")
    else:
        form = DataProcessingAgreementForm(tenant_id=tid)
    return render(request, "dsb/dpa_form.html", {
        "form": form,
        "title": "Neuer Auftragsverarbeitungsvertrag",
    })


@login_required
def dpa_edit(request: HttpRequest, pk) -> HttpResponse:
    """Edit an existing AVV entry."""
    from dsb.forms import DataProcessingAgreementForm
    from dsb.models import DataProcessingAgreement

    tid = _tenant_id(request)
    obj = get_object_or_404(
        DataProcessingAgreement, pk=pk, tenant_id=tid,
    )
    if request.method == "POST":
        form = DataProcessingAgreementForm(
            request.POST, instance=obj, tenant_id=tid,
        )
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by_id = _user_id(request)
            obj.save()
            return redirect("dsb:dpa-list")
    else:
        form = DataProcessingAgreementForm(
            instance=obj, tenant_id=tid,
        )
    return render(request, "dsb/dpa_form.html", {
        "form": form,
        "title": f"AVV bearbeiten: {obj.partner_name}",
        "object": obj,
    })


# -----------------------------------------------------------------------
# CSV Import (VVT / TOM / AVV)
# -----------------------------------------------------------------------


@login_required
@require_module("dsb")
def avv_import(request: HttpRequest) -> HttpResponse:
    """Dedizierter AVV-Import aus CSV-Datei."""
    from django.http import HttpResponse as DjangoResponse
    from dsb.import_csv import import_avv, AVV_CSV_TEMPLATE
    from dsb.models import Mandate

    tid = _tenant_id(request)
    uid = _user_id(request)

    if request.GET.get("template") == "1":
        resp = DjangoResponse(AVV_CSV_TEMPLATE, content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="avv_vorlage.csv"'
        return resp

    result = None
    mandates = Mandate.objects.filter(tenant_id=tid, status="active") if tid else Mandate.objects.none()

    if request.method == "POST":
        mandate_id = request.POST.get("mandate")
        csv_file = request.FILES.get("csv_file")
        if mandate_id and csv_file:
            try:
                mandate = Mandate.objects.get(pk=mandate_id, tenant_id=tid)
                content = csv_file.read().decode("utf-8-sig")
                result = import_avv(content, mandate, tid, uid)
                if result.avv_created:
                    from django.contrib import messages
                    messages.success(
                        request,
                        f"{result.avv_created} AVV importiert, {result.skipped} übersprungen.",
                    )
            except Mandate.DoesNotExist:
                from django.contrib import messages
                messages.error(request, "Mandat nicht gefunden.")
            except Exception as exc:
                from django.contrib import messages
                messages.error(request, f"Import-Fehler: {exc}")

    selected_mandate = None
    if tid and mandates.count() == 1:
        selected_mandate = mandates.first()

    return render(request, "dsb/avv_import.html", {
        "mandates": mandates,
        "selected_mandate": selected_mandate,
        "result": result,
    })


@login_required
@require_module("dsb")
def csv_import(request: HttpRequest) -> HttpResponse:
    """Upload and import VVT / TOM / AVV CSV files."""
    from dsb.forms import CsvImportForm
    from dsb.import_csv import (
        import_csv,
        import_tom,
        import_vvt,
    )
    from dsb.models import Mandate

    tid = _tenant_id(request)
    uid = _user_id(request)
    result = None
    mandate_count = Mandate.objects.filter(
        tenant_id=tid,
    ).count() if tid else 0

    if request.method == "POST":
        form = CsvImportForm(
            request.POST, request.FILES, tenant_id=tid,
        )
        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]
            csv_type = form.cleaned_data["csv_type"]
            mandate = form.cleaned_data["mandate"]
            content = csv_file.read().decode("utf-8-sig")

            if csv_type == "vvt":
                result = import_vvt(
                    content, mandate, tid, uid,
                )
            elif csv_type == "tom":
                result = import_tom(
                    content, mandate, tid, uid,
                )
            else:
                result = import_csv(
                    content, mandate, tid, uid,
                )
    else:
        form = CsvImportForm(tenant_id=tid)

    return render(request, "dsb/import_upload.html", {
        "form": form,
        "result": result,
        "no_mandates": mandate_count == 0,
        "tenant_id": tid,
    })
