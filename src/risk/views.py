"""Risk assessment views."""

from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
)
from django.shortcuts import get_object_or_404, redirect, render

from common.tenant import require_tenant as _require_tenant
from django_tenancy.module_access import require_module
from risk.models import Assessment
from risk.services import (
    ApproveAssessmentCmd,
    CreateAssessmentCmd,
    approve_assessment,
    create_assessment,
)


@login_required
@require_module("risk")
def assessment_list(
    request: HttpRequest,
) -> HttpResponse:
    """List all assessments for current tenant."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        category = request.POST.get("category", "general")

        if not title:
            return HttpResponseBadRequest("Title required")

        create_assessment(
            CreateAssessmentCmd(
                title=title,
                category=category,
            )
        )
        return redirect("risk:assessment_list")

    assessments = (
        Assessment.objects.filter(tenant_id=request.tenant_id)
        .order_by("-created_at")[:100]
    )
    return render(
        request,
        "risk/assessment_list.html",
        {"assessments": assessments},
    )


@login_required
@require_module("risk")
def assessment_detail(
    request: HttpRequest,
    assessment_id: UUID,
) -> HttpResponse:
    """View assessment details."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    assessment = get_object_or_404(
        Assessment,
        id=assessment_id,
        tenant_id=request.tenant_id,
    )
    return render(
        request,
        "risk/assessment_detail.html",
        {"assessment": assessment},
    )


@login_required
@require_module("risk", min_role="manager")
def assessment_approve(
    request: HttpRequest,
    assessment_id: UUID,
) -> HttpResponse:
    """Approve an assessment."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    approve_assessment(ApproveAssessmentCmd(assessment_id=assessment_id))
    return redirect("risk:assessment_list")
