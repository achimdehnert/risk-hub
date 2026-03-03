"""
GBU-Wizard Views (Phase 2C).

5-Schritt HTMX-Wizard:
  Schritt 1 — Stoff + Standort wählen
  Schritt 2 — Tätigkeitsdaten erfassen
  Schritt 3 — Gefährdungskategorien bestätigen (HTMX-Partial)
  Schritt 4 — Maßnahmen bestätigen (HTMX-Partial)
  Schritt 5 — Freigabe

Pattern: Views nur HTTP, keine Business-Logik → gbu_engine.py
HTMX-Detection: request.headers.get("HX-Request") (kein django_htmx)
"""
import logging
import uuid
from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from gbu.forms import (
    WizardStep2Form,
    WizardStep3Form,
    WizardStep4Form,
    WizardStep5Form,
)
from gbu.models.activity import ActivityStatus, HazardAssessmentActivity
from gbu.services.gbu_engine import (
    ApproveActivityCmd,
    CreateActivityCmd,
    approve_activity,
    create_activity,
    derive_hazard_categories,
    set_risk_score,
)

logger = logging.getLogger(__name__)

_RISK_BADGE = {
    "low":      ("bg-green-100 text-green-800",   "Gering"),
    "medium":   ("bg-yellow-100 text-yellow-800", "Mittel"),
    "high":     ("bg-orange-100 text-orange-800", "Hoch"),
    "critical": ("bg-red-100 text-red-800",       "Kritisch"),
}


def _tenant_id(request: HttpRequest) -> UUID:
    return UUID(str(request.tenant_id))


# ── Aktivitätsliste ────────────────────────────────────────────────────────────

@login_required
@require_GET
def activity_list(request: HttpRequest) -> HttpResponse:
    tenant_id = _tenant_id(request)
    activities = (
        HazardAssessmentActivity.objects
        .filter(tenant_id=tenant_id)
        .select_related("site", "sds_revision")
        .order_by("-created_at")
    )
    return render(request, "gbu/activity_list.html", {
        "activities": activities,
        "status_choices": ActivityStatus,
        "risk_badge": _RISK_BADGE,
    })


# ── Schritt 1: Stoff + Standort ────────────────────────────────────────────────

@login_required
@require_GET
def wizard_step1(request: HttpRequest) -> HttpResponse:
    from substances.models import SdsRevision
    from tenancy.models import Site

    tenant_id = _tenant_id(request)
    revisions = (
        SdsRevision.objects
        .filter(tenant_id=tenant_id)
        .select_related("substance")
        .order_by("substance__name")
    )
    sites = Site.objects.filter(tenant_id=tenant_id).order_by("name")
    return render(request, "gbu/wizard_step1.html", {
        "step": 1,
        "revisions": revisions,
        "sites": sites,
    })


# ── Schritt 2: Tätigkeitsdaten ─────────────────────────────────────────────────

@login_required
def wizard_step2(request: HttpRequest) -> HttpResponse:
    sds_revision_id = (
        request.GET.get("sds_revision_id")
        or request.POST.get("sds_revision_id")
    )
    site_id = request.GET.get("site_id") or request.POST.get("site_id")

    if not sds_revision_id or not site_id:
        return redirect("gbu:wizard-step1")

    if request.method == "POST":
        form = WizardStep2Form(request.POST)
        if form.is_valid():
            request.session["gbu_wizard"] = {
                "sds_revision_id": sds_revision_id,
                "site_id": site_id,
                **form.cleaned_data,
                "substitution_checked": form.cleaned_data.get(
                    "substitution_checked", False
                ),
            }
            return redirect("gbu:wizard-step3")
    else:
        form = WizardStep2Form()

    from substances.models import SdsRevision
    revision = get_object_or_404(SdsRevision, id=sds_revision_id)

    return render(request, "gbu/wizard_step2.html", {
        "step": 2,
        "form": form,
        "revision": revision,
        "sds_revision_id": sds_revision_id,
        "site_id": site_id,
    })


# ── Schritt 3: Gefährdungskategorien ──────────────────────────────────────────

@login_required
def wizard_step3(request: HttpRequest) -> HttpResponse:
    wizard = request.session.get("gbu_wizard", {})
    sds_revision_id = wizard.get("sds_revision_id")
    if not sds_revision_id:
        return redirect("gbu:wizard-step1")

    categories = derive_hazard_categories(UUID(sds_revision_id))

    if request.method == "POST":
        form = WizardStep3Form(request.POST)
        if form.is_valid():
            wizard["_step3_confirmed"] = True
            request.session["gbu_wizard"] = wizard
            return redirect("gbu:wizard-step4")
    else:
        form = WizardStep3Form()

    return render(request, "gbu/wizard_step3.html", {
        "step": 3,
        "form": form,
        "categories": categories,
        "is_htmx": request.headers.get("HX-Request"),
    })


# ── HTMX Partial: Gefährdungsliste ────────────────────────────────────────────

@login_required
@require_GET
def partial_hazard_list(request: HttpRequest) -> HttpResponse:
    sds_revision_id = request.GET.get("sds_revision_id")
    if not sds_revision_id:
        return HttpResponse("")
    try:
        categories = derive_hazard_categories(UUID(sds_revision_id))
    except Exception:
        categories = []
    return render(request, "gbu/partials/_hazard_list.html", {
        "categories": categories,
    })


# ── Schritt 4: Maßnahmen ──────────────────────────────────────────────────────

@login_required
def wizard_step4(request: HttpRequest) -> HttpResponse:
    wizard = request.session.get("gbu_wizard", {})
    sds_revision_id = wizard.get("sds_revision_id")
    if not sds_revision_id or not wizard.get("_step3_confirmed"):
        return redirect("gbu:wizard-step3")

    categories = derive_hazard_categories(UUID(sds_revision_id))

    from gbu.models.reference import MeasureTemplate
    category_ids = [c.id for c in categories]
    templates = MeasureTemplate.objects.filter(
        category_id__in=category_ids
    ).order_by("tops_type", "sort_order")

    if request.method == "POST":
        form = WizardStep4Form(request.POST)
        if form.is_valid():
            wizard["_confirmed_measure_ids"] = form.get_confirmed_ids()
            wizard["_step4_confirmed"] = True
            request.session["gbu_wizard"] = wizard
            return redirect("gbu:wizard-step5")
    else:
        form = WizardStep4Form()

    return render(request, "gbu/wizard_step4.html", {
        "step": 4,
        "form": form,
        "templates": templates,
    })


# ── HTMX Partial: Maßnahmenliste ──────────────────────────────────────────────

@login_required
@require_GET
def partial_measure_list(request: HttpRequest) -> HttpResponse:
    sds_revision_id = request.GET.get("sds_revision_id")
    if not sds_revision_id:
        return HttpResponse("")
    try:
        categories = derive_hazard_categories(UUID(sds_revision_id))
        from gbu.models.reference import MeasureTemplate
        category_ids = [c.id for c in categories]
        templates = MeasureTemplate.objects.filter(
            category_id__in=category_ids
        ).order_by("tops_type", "sort_order")
    except Exception:
        templates = []
    return render(request, "gbu/partials/_measure_list.html", {
        "templates": templates,
    })


# ── Schritt 5: Freigabe ───────────────────────────────────────────────────────

@login_required
def wizard_step5(request: HttpRequest) -> HttpResponse:
    wizard = request.session.get("gbu_wizard", {})
    if not wizard.get("_step4_confirmed"):
        return redirect("gbu:wizard-step4")

    tenant_id = _tenant_id(request)
    user_id = UUID(str(request.user.id)) if request.user.id else uuid.uuid4()

    if request.method == "POST":
        form = WizardStep5Form(request.POST)
        if form.is_valid():
            try:
                cmd = CreateActivityCmd(
                    site_id=UUID(wizard["site_id"]),
                    sds_revision_id=UUID(wizard["sds_revision_id"]),
                    activity_description=wizard["activity_description"],
                    activity_frequency=wizard["activity_frequency"],
                    duration_minutes=wizard["duration_minutes"],
                    quantity_class=wizard["quantity_class"],
                    substitution_checked=wizard.get("substitution_checked", False),
                    substitution_notes=wizard.get("substitution_notes", ""),
                )
                activity = create_activity(
                    cmd=cmd, tenant_id=tenant_id, user_id=user_id
                )
                set_risk_score(activity_id=activity.id, tenant_id=tenant_id)

                approve_cmd = ApproveActivityCmd(
                    activity_id=activity.id,
                    next_review_date=form.cleaned_data["next_review_date"],
                )
                approve_activity(
                    cmd=approve_cmd,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    approved_by_name=form.cleaned_data["approved_by_name"],
                )

                request.session.pop("gbu_wizard", None)
                return redirect("gbu:activity-detail", pk=activity.id)

            except Exception as exc:
                logger.exception("[GBU Wizard] Fehler bei Freigabe: %s", exc)
                form.add_error(None, "Fehler bei der Freigabe. Bitte erneut versuchen.")
    else:
        form = WizardStep5Form()

    return render(request, "gbu/wizard_step5.html", {
        "step": 5,
        "form": form,
        "wizard": wizard,
    })


# ── Detail-Ansicht ────────────────────────────────────────────────────────────

@login_required
@require_GET
def activity_detail(request: HttpRequest, pk: UUID) -> HttpResponse:
    tenant_id = _tenant_id(request)
    activity = get_object_or_404(
        HazardAssessmentActivity.objects.select_related(
            "site", "sds_revision"
        ).prefetch_related("measures", "derived_hazard_categories"),
        id=pk,
        tenant_id=tenant_id,
    )
    badge_css, badge_label = _RISK_BADGE.get(
        activity.risk_score,
        ("bg-gray-100 text-gray-800", activity.risk_score),
    )
    is_htmx = request.headers.get("HX-Request")
    template = (
        "gbu/partials/_activity_detail.html"
        if is_htmx
        else "gbu/activity_detail.html"
    )
    return render(request, template, {
        "activity": activity,
        "badge_css": badge_css,
        "badge_label": badge_label,
    })


# ── HTMX Partial: Risiko-Badge ────────────────────────────────────────────────

@login_required
@require_GET
def partial_risk_badge(request: HttpRequest) -> HttpResponse:
    quantity_class = request.GET.get("quantity_class", "")
    activity_frequency = request.GET.get("activity_frequency", "")
    has_cmr = request.GET.get("has_cmr", "false").lower() == "true"

    if not quantity_class or not activity_frequency:
        return HttpResponse("")

    from gbu.services.gbu_engine import calculate_risk_score
    score = calculate_risk_score(quantity_class, activity_frequency, has_cmr)
    badge_css, badge_label = _RISK_BADGE.get(
        score, ("bg-gray-100 text-gray-800", score)
    )

    return render(request, "gbu/partials/_risk_badge.html", {
        "score": score,
        "badge_css": badge_css,
        "badge_label": badge_label,
    })
