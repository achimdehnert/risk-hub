"""Views für SDS-Änderungsprotokoll (UC-005), Compliance-Review (UC-006), Kataster-Revision (UC-007)."""

import logging
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

ITEMS_PER_PAGE = 25

from .models import ComplianceReview, KatasterRevision, SdsChangeLog, SubstanceUsage

logger = logging.getLogger(__name__)


def _tid(request):
    return getattr(request, "tenant_id", None)


# =========================================================================
# UC-005: SDS Change Log
# =========================================================================


@login_required
def changelog_list(request: HttpRequest) -> HttpResponse:
    """SDS-Änderungsprotokolle — Übersicht (UC-005)."""
    tenant_id = _tid(request)
    impact_filter = request.GET.get("impact", "")

    logs = (
        SdsChangeLog.objects.filter(tenant_id=tenant_id)
        .select_related("product", "old_revision", "new_revision")
        .order_by("-created_at")
    )
    if impact_filter:
        logs = logs.filter(impact=impact_filter)

    stats = {
        "total": logs.count(),
        "action_required": logs.filter(impact="action_required").count(),
        "unreviewed": logs.filter(reviewed_at__isnull=True).count(),
    }

    paginator = Paginator(logs, ITEMS_PER_PAGE)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "substances/compliance/changelog_list.html",
        {
            "logs": page,
            "page_obj": page,
            "stats": stats,
            "impact_filter": impact_filter,
        },
    )


@login_required
def changelog_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Einzelnes SDS-Änderungsprotokoll (UC-005)."""
    tenant_id = _tid(request)
    log = get_object_or_404(SdsChangeLog, pk=pk, tenant_id=tenant_id)

    if request.method == "POST" and "mark_reviewed" in request.POST:
        log.reviewed_by = getattr(request.user, "pk", None)
        log.reviewed_at = timezone.now()
        log.notes = request.POST.get("notes", log.notes)
        log.save(update_fields=["reviewed_by", "reviewed_at", "notes", "updated_at"])
        messages.success(request, "Änderungsprotokoll als geprüft markiert.")
        return redirect("compliance:changelog_detail", pk=pk)

    return render(request, "substances/compliance/changelog_detail.html", {"log": log})


# =========================================================================
# UC-006: Compliance Review
# =========================================================================


@login_required
def review_dashboard(request: HttpRequest) -> HttpResponse:
    """Compliance-Review Dashboard — Übersicht fällige Prüfungen (UC-006)."""
    tenant_id = _tid(request)
    today = date.today()
    soon = today + timedelta(days=30)

    usages = SubstanceUsage.objects.filter(tenant_id=tenant_id).select_related(
        "product",
        "site",
        "department",
    )
    reviews = ComplianceReview.objects.filter(tenant_id=tenant_id)

    overdue_usages = usages.filter(
        Q(compliance_reviews__next_review_date__lt=today) | Q(compliance_reviews__isnull=True),
    ).distinct()

    upcoming_usages = usages.filter(
        compliance_reviews__next_review_date__gte=today,
        compliance_reviews__next_review_date__lte=soon,
    ).distinct()

    stats = {
        "total_usages": usages.count(),
        "total_reviews": reviews.count(),
        "overdue": overdue_usages.count(),
        "upcoming": upcoming_usages.filter(
            compliance_reviews__next_review_date__lte=soon,
        ).count(),
        "current": reviews.filter(result="current").count(),
        "update_required": reviews.filter(result="update_required").count(),
    }

    recent_reviews = reviews.select_related(
        "substance_usage__product",
        "substance_usage__site",
    ).order_by("-review_date")[:10]

    return render(
        request,
        "substances/compliance/review_dashboard.html",
        {
            "stats": stats,
            "overdue_usages": overdue_usages[:20],
            "upcoming_usages": upcoming_usages[:20],
            "recent_reviews": recent_reviews,
            "today": today,
        },
    )


@login_required
def review_create(request: HttpRequest, usage_id: int) -> HttpResponse:
    """Neue Compliance-Prüfung für eine Verwendung erstellen (UC-006)."""
    tenant_id = _tid(request)
    usage = get_object_or_404(SubstanceUsage, pk=usage_id, tenant_id=tenant_id)

    if request.method == "POST":
        result = request.POST.get("result", "current")
        comment = request.POST.get("comment", "")
        next_date = request.POST.get("next_review_date")

        if not next_date:
            next_date = date.today() + timedelta(days=730)

        ComplianceReview.objects.create(
            tenant_id=tenant_id,
            substance_usage=usage,
            reviewer_id=getattr(request.user, "pk", None),
            review_date=date.today(),
            result=result,
            next_review_date=next_date,
            comment=comment,
        )
        messages.success(request, f"Prüfung für '{usage.product.trade_name}' dokumentiert.")
        return redirect("compliance:review_dashboard")

    return render(
        request,
        "substances/compliance/review_form.html",
        {
            "usage": usage,
            "title": f"Compliance-Prüfung: {usage.product.trade_name}",
            "result_choices": ComplianceReview.Result.choices,
        },
    )


@login_required
def review_list(request: HttpRequest) -> HttpResponse:
    """Alle Compliance-Prüfungen (UC-006)."""
    tenant_id = _tid(request)
    qs = (
        ComplianceReview.objects.filter(tenant_id=tenant_id)
        .select_related("substance_usage__product", "substance_usage__site")
        .order_by("-review_date")
    )
    paginator = Paginator(qs, ITEMS_PER_PAGE)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "substances/compliance/review_list.html",
        {
            "reviews": page,
            "page_obj": page,
        },
    )


# =========================================================================
# UC-007: Kataster Revision
# =========================================================================


@login_required
def revision_list(request: HttpRequest) -> HttpResponse:
    """Kataster-Revisionen — Übersicht (UC-007)."""
    tenant_id = _tid(request)
    qs = (
        KatasterRevision.objects.filter(tenant_id=tenant_id)
        .select_related("site")
        .order_by("-created_at")
    )

    stats = {
        "total": qs.count(),
        "draft": KatasterRevision.objects.filter(tenant_id=tenant_id, status="draft").count(),
        "approved": KatasterRevision.objects.filter(tenant_id=tenant_id, status="approved").count(),
    }

    paginator = Paginator(qs, ITEMS_PER_PAGE)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "substances/compliance/revision_list.html",
        {
            "revisions": page,
            "page_obj": page,
            "stats": stats,
        },
    )


@login_required
def revision_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Kataster-Revision Detail mit Snapshot und Changelog (UC-007)."""
    tenant_id = _tid(request)
    rev = get_object_or_404(KatasterRevision, pk=pk, tenant_id=tenant_id)

    return render(
        request,
        "substances/compliance/revision_detail.html",
        {
            "revision": rev,
            "snapshot_count": len(rev.snapshot) if isinstance(rev.snapshot, list) else 0,
            "changelog": rev.changelog if isinstance(rev.changelog, dict) else {},
        },
    )


@login_required
def revision_create(request: HttpRequest) -> HttpResponse:
    """Neue Kataster-Revision erstellen (UC-007)."""
    tenant_id = _tid(request)

    from tenancy.models import Site

    sites = Site.objects.filter(tenant_id=tenant_id, is_active=True).order_by("name")

    if request.method == "POST":
        site_id = request.POST.get("site")
        notes = request.POST.get("notes", "")

        if not site_id:
            messages.error(request, "Bitte einen Standort wählen.")
            return render(
                request,
                "substances/compliance/revision_form.html",
                {
                    "sites": sites,
                    "title": "Neue Kataster-Revision",
                },
            )

        site = get_object_or_404(Site, pk=site_id, tenant_id=tenant_id)

        last_rev = (
            KatasterRevision.objects.filter(
                tenant_id=tenant_id,
                site=site,
            )
            .order_by("-revision_number")
            .first()
        )
        next_num = (last_rev.revision_number + 1) if last_rev else 1

        usages = SubstanceUsage.objects.filter(
            tenant_id=tenant_id,
            site=site,
        ).select_related("product")

        snapshot = [
            {
                "product_id": u.product_id,
                "trade_name": u.product.trade_name,
                "manufacturer": getattr(u.product, "manufacturer_name", ""),
                "department": str(u.department) if u.department else "",
                "storage_location": u.storage_location or "",
            }
            for u in usages
        ]

        changelog = {"added": [], "changed": [], "removed": []}
        if last_rev and isinstance(last_rev.snapshot, list):
            old_ids = {e.get("product_id") for e in last_rev.snapshot}
            new_ids = {e["product_id"] for e in snapshot}
            changelog["added"] = [e for e in snapshot if e["product_id"] not in old_ids]
            changelog["removed"] = [
                e for e in last_rev.snapshot if e.get("product_id") not in new_ids
            ]

        rev = KatasterRevision.objects.create(
            tenant_id=tenant_id,
            site=site,
            revision_number=next_num,
            status="draft",
            snapshot=snapshot,
            changelog=changelog,
            notes=notes,
        )
        messages.success(request, f"Kataster-Revision {next_num} für {site.name} erstellt.")
        return redirect("compliance:revision_detail", pk=rev.pk)

    return render(
        request,
        "substances/compliance/revision_form.html",
        {
            "sites": sites,
            "title": "Neue Kataster-Revision",
        },
    )


@login_required
def revision_approve(request: HttpRequest, pk: int) -> HttpResponse:
    """Kataster-Revision freigeben (UC-007)."""
    tenant_id = _tid(request)
    rev = get_object_or_404(KatasterRevision, pk=pk, tenant_id=tenant_id)

    if request.method != "POST":
        return redirect("compliance:revision_detail", pk=pk)

    if rev.status == "approved":
        messages.warning(request, "Revision bereits freigegeben.")
        return redirect("compliance:revision_detail", pk=pk)

    KatasterRevision.objects.filter(
        tenant_id=tenant_id,
        site=rev.site,
        status="approved",
    ).update(status="superseded")

    rev.status = "approved"
    rev.approved_by = getattr(request.user, "pk", None)
    rev.approved_at = timezone.now()
    rev.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    messages.success(request, f"Kataster-Revision {rev.revision_number} freigegeben.")
    return redirect("compliance:revision_detail", pk=pk)
