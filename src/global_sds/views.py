# src/global_sds/views.py
"""
Views für Global SDS Library Frontend (ADR-012).

Compliance Dashboard, SDS Upload, Diff-Panel, Adopt/Defer.
Service-Layer Pattern: Views → Services → Models.
"""

import logging
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q  # noqa: F401 — used in future filters
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from global_sds.forms import (
    DeferUpdateForm,
    GlobalSdsUploadForm,
    RevisionEditForm,
)
from global_sds.sds_usage import SdsUsage, SdsUsageStatus
from global_sds.services import (
    SdsUploadPipeline,
    SdsUsageService,
    get_diff_record,
    get_sds_usage_for_revision,
    get_sds_usages,
    get_tenant_revisions,
    get_visible_revisions,
)

logger = logging.getLogger(__name__)


def _tenant_id(request: HttpRequest) -> str:
    """Tenant-ID aus Request extrahieren."""
    return str(getattr(request, "tenant_id", ""))


# ─────────────────────────────────────────────────────────────────────
# Compliance Dashboard
# ─────────────────────────────────────────────────────────────────────


@login_required
@require_GET
def compliance_dashboard(request: HttpRequest) -> HttpResponse:
    """
    SDS Compliance Dashboard (ADR-012 §8).

    KPI-Kacheln, Deadline-Ampel, Review-Tabelle.
    """
    tenant_id = _tenant_id(request)
    today = date.today()
    soon_cutoff = today + timedelta(days=14)

    usages = get_sds_usages(tenant_id)

    # Alle Revisionen die dieser Tenant sehen darf
    all_revisions = (
        get_visible_revisions(tenant_id)
        .select_related("substance")
        .order_by("-created_at")
    )
    total_revisions = all_revisions.count()

    # KPI-Zähler
    critical_count = usages.filter(
        status=SdsUsageStatus.REVIEW_REQUIRED,
    ).count()
    regulatory_count = usages.filter(
        status=SdsUsageStatus.UPDATE_AVAILABLE,
    ).count()
    active_count = usages.filter(
        status=SdsUsageStatus.ACTIVE,
    ).count()

    # Overdue + Soon
    overdue = (
        usages.filter(
            review_deadline__lt=today,
            status__in=[
                SdsUsageStatus.REVIEW_REQUIRED,
                SdsUsageStatus.UPDATE_AVAILABLE,
            ],
        )
        .select_related("sds_revision__substance")
        .order_by(
            "review_deadline",
        )
    )

    due_soon = (
        usages.filter(
            review_deadline__gte=today,
            review_deadline__lte=soon_cutoff,
            status__in=[
                SdsUsageStatus.REVIEW_REQUIRED,
                SdsUsageStatus.UPDATE_AVAILABLE,
            ],
        )
        .select_related("sds_revision__substance")
        .order_by(
            "review_deadline",
        )
    )

    pending_review = (
        usages.filter(
            status__in=[
                SdsUsageStatus.REVIEW_REQUIRED,
                SdsUsageStatus.UPDATE_AVAILABLE,
            ],
        )
        .select_related(
            "sds_revision__substance",
            "pending_update_revision",
        )
        .order_by("review_deadline")
    )

    # GBU geflaggt (falls Modul vorhanden)
    gbu_flagged = 0
    try:
        from gbu.services import get_hazard_assessment_activities

        gbu_flagged = get_hazard_assessment_activities(tenant_id).filter(
            review_required=True,
        ).count()
    except (ImportError, Exception):
        pass

    context = {
        "critical_count": critical_count,
        "regulatory_count": regulatory_count,
        "gbu_flagged": gbu_flagged,
        "active_count": active_count,
        "total_revisions": total_revisions,
        "all_revisions": all_revisions[:50],
        "overdue": overdue,
        "due_soon": due_soon,
        "pending_review": pending_review,
        "today": today,
    }

    return render(
        request,
        "global_sds/compliance_dashboard.html",
        context,
    )


# ─────────────────────────────────────────────────────────────────────
# SDS Upload (globale Pipeline)
# ─────────────────────────────────────────────────────────────────────


@login_required
def sds_upload(request: HttpRequest) -> HttpResponse:
    """SDS-PDF Upload in die globale Pipeline (ADR-012 §5)."""
    if request.method == "GET":
        form = GlobalSdsUploadForm()
        return render(
            request,
            "global_sds/sds_upload.html",
            {"form": form},
        )

    form = GlobalSdsUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(
            request,
            "global_sds/sds_upload.html",
            {"form": form},
        )

    pdf_file = request.FILES["pdf_file"]
    pdf_bytes = pdf_file.read()
    tenant_id = _tenant_id(request)

    # Parser aufrufen
    try:
        from substances.services.sds_parser import SdsParserService

        parser = SdsParserService()
        parse_result = parser.parse_pdf(pdf_file)
    except (ImportError, Exception) as exc:
        logger.warning("SDS parser error: %s", exc)
        parse_result = {
            "product_name": pdf_file.name.replace(".pdf", ""),
            "parse_confidence": 0.0,
        }

    # Pipeline verarbeiten
    pipeline = SdsUploadPipeline()
    result = pipeline.process(
        pdf_bytes=pdf_bytes,
        parse_result=parse_result,
        tenant_id=tenant_id,
    )

    messages.info(request, f"{result.outcome}: {result.message}")

    if result.revision:
        return redirect(
            "global_sds:revision-detail",
            pk=result.revision.pk,
        )
    return redirect("global_sds:dashboard")


# ─────────────────────────────────────────────────────────────────────
# Revision Detail
# ─────────────────────────────────────────────────────────────────────


@login_required
@require_GET
def revision_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Detail-Ansicht einer globalen SDS-Revision."""
    tenant_id = _tenant_id(request)
    revision = get_object_or_404(
        get_visible_revisions(tenant_id),
        pk=pk,
    )

    components = revision.components.all()
    exposure_limits = revision.exposure_limits.select_related(
        "component",
    ).all()

    usage = get_sds_usage_for_revision(tenant_id, revision)

    raw = revision.raw_data or {}
    context = {
        "revision": revision,
        "substance": revision.substance,
        "components": components,
        "exposure_limits": exposure_limits,
        "usage": usage,
        "h_statements": revision.hazard_statements.all(),
        "p_statements": revision.precautionary_statements.all(),
        "pictograms": revision.pictograms.all(),
        "sds_sections": raw.get("_sections", {}),
        "raw_text_length": len(raw.get("_raw_text", "")),
    }

    return render(
        request,
        "global_sds/revision_detail.html",
        context,
    )


# ─────────────────────────────────────────────────────────────────────
# Revision Edit / Delete
# ─────────────────────────────────────────────────────────────────────


@login_required
def revision_edit(
    request: HttpRequest,
    pk: int,
) -> HttpResponse:
    """SDS-Revision bearbeiten (Metadaten + regulatorisch)."""
    tenant_id = _tenant_id(request)
    revision = get_object_or_404(
        get_visible_revisions(tenant_id),
        pk=pk,
    )

    if request.method == "GET":
        form = RevisionEditForm(instance=revision)
        return render(
            request,
            "global_sds/revision_edit.html",
            {"form": form, "revision": revision},
        )

    form = RevisionEditForm(
        request.POST,
        instance=revision,
    )
    if not form.is_valid():
        return render(
            request,
            "global_sds/revision_edit.html",
            {"form": form, "revision": revision},
        )

    from common.services import save_form

    save_form(form, tenant_id, is_create=False)
    messages.success(request, "SDS-Revision aktualisiert.")
    return redirect(
        "global_sds:revision-detail",
        pk=revision.pk,
    )


@login_required
@require_POST
def revision_delete(
    request: HttpRequest,
    pk: int,
) -> HttpResponse:
    """SDS-Revision löschen (nur eigene PENDING)."""
    tenant_id = _tenant_id(request)
    revision = get_object_or_404(
        get_tenant_revisions(tenant_id),
        pk=pk,
    )

    from common.services import delete_object

    name = str(revision)
    delete_object(revision)
    messages.success(
        request,
        f"SDS-Revision '{name}' gelöscht.",
    )
    return redirect("global_sds:dashboard")


# ─────────────────────────────────────────────────────────────────────
# HTMX Partials: Diff-Panel, Adopt, Defer
# ─────────────────────────────────────────────────────────────────────


@login_required
@require_GET
def diff_panel(request: HttpRequest, pk: int) -> HttpResponse:
    """HTMX: Diff-Panel für eine SdsUsage laden (ADR-012 §8.4)."""
    tenant_id = _tenant_id(request)
    usage = get_object_or_404(
        SdsUsage,
        pk=pk,
        tenant_id=tenant_id,
    )

    diff_record = None
    if usage.pending_update_revision and usage.sds_revision:
        diff_record = get_diff_record(usage.sds_revision, usage.pending_update_revision)

    context = {
        "usage": usage,
        "diff_record": diff_record,
        "old_revision": usage.sds_revision,
        "new_revision": usage.pending_update_revision,
    }

    return render(
        request,
        "global_sds/partials/_diff_panel.html",
        context,
    )


@login_required
@require_POST
def adopt_update(request: HttpRequest, pk: int) -> HttpResponse:
    """HTMX: Neue Version übernehmen (ADR-012 §8.4)."""
    tenant_id = _tenant_id(request)
    usage = get_object_or_404(
        SdsUsage,
        pk=pk,
        tenant_id=tenant_id,
    )

    service = SdsUsageService()
    try:
        new_usage = service.adopt_update(usage, request.user)
        messages.success(
            request,
            f"Update übernommen: {new_usage.sds_revision}",
        )
    except ValueError as exc:
        messages.error(request, str(exc))

    if getattr(request, "htmx", None):
        return render(
            request,
            "global_sds/partials/_usage_row.html",
            {"usage": new_usage if "new_usage" in dir() else usage},
        )
    return redirect("global_sds:dashboard")


@login_required
def defer_update(request: HttpRequest, pk: int) -> HttpResponse:
    """HTMX: Update zurückstellen mit Pflichtbegründung."""
    tenant_id = _tenant_id(request)
    usage = get_object_or_404(
        SdsUsage,
        pk=pk,
        tenant_id=tenant_id,
    )

    if request.method == "GET":
        form = DeferUpdateForm()
        return render(
            request,
            "global_sds/partials/_defer_modal.html",
            {"form": form, "usage": usage},
        )

    form = DeferUpdateForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "global_sds/partials/_defer_modal.html",
            {"form": form, "usage": usage},
        )

    service = SdsUsageService()
    try:
        service.defer_update(
            usage=usage,
            user=request.user,
            reason=form.cleaned_data["reason"],
            deferred_until=form.cleaned_data.get("deferred_until"),
        )
        messages.success(request, "Update zurückgestellt.")
    except ValueError as exc:
        messages.error(request, str(exc))

    if getattr(request, "htmx", None):
        return render(
            request,
            "global_sds/partials/_usage_row.html",
            {"usage": usage},
        )
    return redirect("global_sds:dashboard")
