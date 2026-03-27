"""Project views (ADR-041).

Views handle HTTP only — business logic in services.py.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from common.tenant import require_tenant as _require_tenant
from projects.models import Project
from projects.services import (
    CreateProjectCmd,
    create_project,
    get_subscribed_modules,
    recommend_modules_from_description,
)

logger = logging.getLogger(__name__)


@login_required
def project_list(request: HttpRequest) -> HttpResponse:
    """List all projects for current tenant."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    projects = (
        Project.objects.filter(tenant_id=request.tenant_id)
        .prefetch_related("modules")
        .order_by("-created_at")[:100]
    )
    return render(
        request,
        "projects/project_list.html",
        {"projects": projects},
    )


@login_required
def project_create(request: HttpRequest) -> HttpResponse:
    """Create a new project with KI module recommendation."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    from tenancy.models import Site

    sites = Site.objects.filter(tenant_id=request.tenant_id)
    subscribed = get_subscribed_modules(request.tenant_id)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        site_id = request.POST.get("site_id", "")
        description = request.POST.get("description", "")
        project_number = request.POST.get("project_number", "")
        client_name = request.POST.get("client_name", "")
        selected = request.POST.getlist("modules")
        declined = request.POST.getlist("declined_modules")

        if not name or not site_id:
            recommendations = recommend_modules_from_description(
                description, subscribed,
            )
            return render(
                request,
                "projects/project_create.html",
                {
                    "sites": sites,
                    "recommendations": recommendations,
                    "subscribed_modules": subscribed,
                    "error": "Name und Standort sind Pflichtfelder.",
                    "form_data": request.POST,
                },
            )

        # Build recommendations for storage
        recommendations = recommend_modules_from_description(
            description, subscribed,
        )

        project = create_project(
            CreateProjectCmd(
                tenant_id=str(request.tenant_id),
                site_id=site_id,
                name=name,
                description=description,
                project_number=project_number,
                client_name=client_name,
                created_by_id=request.user.pk,
                selected_modules=selected,
                declined_modules=declined,
                module_recommendations=recommendations,
            )
        )
        return redirect("projects:project-detail", pk=project.pk)

    # GET: empty form
    recommendations = recommend_modules_from_description(
        "", subscribed,
    )
    return render(
        request,
        "projects/project_create.html",
        {
            "sites": sites,
            "recommendations": recommendations,
            "subscribed_modules": subscribed,
        },
    )


@login_required
def project_recommend_modules(
    request: HttpRequest,
) -> HttpResponse:
    """HTMX endpoint: return module recommendations for description."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    description = request.POST.get("description", "")
    subscribed = get_subscribed_modules(request.tenant_id)
    recommendations = recommend_modules_from_description(
        description, subscribed,
    )
    return render(
        request,
        "projects/partials/_module_recommendations.html",
        {
            "recommendations": recommendations,
            "subscribed_modules": subscribed,
        },
    )


@login_required
def project_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Project detail / dashboard view."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    project = get_object_or_404(
        Project.objects.prefetch_related("modules"),
        pk=pk,
        tenant_id=request.tenant_id,
    )

    from projects.services import AVAILABLE_MODULES

    active_modules = project.modules.filter(status="active")
    module_details = []
    for pm in active_modules:
        meta = AVAILABLE_MODULES.get(pm.module, {})
        module_details.append({
            "code": pm.module,
            "label": meta.get("label", pm.module),
            "icon": meta.get("icon", "box"),
            "description": meta.get("description", ""),
        })

    declined = project.modules.filter(status="declined")

    return render(
        request,
        "projects/project_detail.html",
        {
            "project": project,
            "module_details": module_details,
            "declined_modules": declined,
        },
    )
