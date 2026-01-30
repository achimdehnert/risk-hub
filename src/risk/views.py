"""Risk assessment views."""

from uuid import UUID

from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.shortcuts import get_object_or_404, redirect, render

from risk.models import Assessment
from risk.services import (
    ApproveAssessmentCmd,
    CreateAssessmentCmd,
    approve_assessment,
    create_assessment,
)


def _require_tenant(
    request: HttpRequest,
) -> HttpResponse | None:
    tenant_id = getattr(request, "tenant_id", None)
    if tenant_id is None:
        return HttpResponseForbidden("Missing tenant")
    return None


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
