"""Views for the module shop configurator.

Include in your app's urls.py::

    from django.urls import include, path
    path("billing/modules/", include("django_module_shop.urls")),

Requires LOGIN_URL to be set. Views enforce authentication via
LoginRequiredMixin and optionally check for tenant-admin role.

Template paths (override in your project's templates/ dir):
    django_module_shop/configurator.html
    django_module_shop/partials/module_card.html
    django_module_shop/partials/configurator_summary.html
"""

from __future__ import annotations

import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View
from django.views.generic import TemplateView

from .catalogue import get_catalogue, get_modules_by_category
from .services import activate_module, apply_module_set, get_active_modules, get_subscription_map

logger = logging.getLogger(__name__)


def _get_org(request: HttpRequest):
    """Resolve Organization from request.tenant_id. Returns None if not found."""
    tenant_id = getattr(request, "tenant_id", None)
    if not tenant_id:
        return None
    try:
        from django_tenancy.models import Organization

        return Organization.objects.filter(tenant_id=tenant_id).first()
    except Exception:
        return None


class ModuleConfiguratorView(LoginRequiredMixin, TemplateView):
    """Main module configurator page.

    Shows all available modules with their current subscription status.
    Tenant admin can toggle modules on/off and save the configuration.

    Context:
        catalogue:        dict[str, ModuleDefinition]
        by_category:      dict[str, list[ModuleDefinition]]
        active_modules:   set[str]
        subscription_map: dict[str, ModuleSubscription]
        organization:     Organization | None
    """

    template_name = "django_module_shop/configurator.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        org = _get_org(self.request)
        tenant_id = getattr(self.request, "tenant_id", None)

        ctx["catalogue"] = get_catalogue()
        ctx["by_category"] = get_modules_by_category()
        ctx["active_modules"] = get_active_modules(tenant_id) if tenant_id else set()
        ctx["subscription_map"] = get_subscription_map(tenant_id) if tenant_id else {}
        ctx["organization"] = org
        return ctx


class ModuleToggleView(LoginRequiredMixin, View):
    """HTMX endpoint: toggle a single module on or off.

    POST /modules/toggle/
    Body: {"module": "risk", "active": true}

    Returns 200 with updated module card partial (HTMX swap).
    Returns 400 on invalid input, 403 if not tenant admin.
    """

    def post(self, request: HttpRequest) -> HttpResponse:
        org = _get_org(request)
        if not org:
            return HttpResponse("No tenant context", status=403)

        try:
            data = json.loads(request.body)
            module_code = str(data["module"])
            activate = bool(data.get("active", True))
        except (KeyError, ValueError, json.JSONDecodeError):
            return HttpResponse("Invalid request body", status=400)

        catalogue = get_catalogue()
        if module_code not in catalogue:
            return HttpResponse(f"Unknown module: {module_code}", status=400)

        if activate:
            activate_module(org, module_code)
        else:
            from .services import deactivate_module

            deactivate_module(org, module_code)

        tenant_id = getattr(request, "tenant_id", None)
        active_modules = get_active_modules(tenant_id) if tenant_id else set()

        # Return HTMX partial for the toggled card
        from django.template.loader import render_to_string

        html = render_to_string(
            "django_module_shop/partials/module_card.html",
            {
                "module": catalogue[module_code],
                "active_modules": active_modules,
                "organization": org,
            },
            request=request,
        )
        return HttpResponse(html)


class ModuleApplyView(LoginRequiredMixin, View):
    """Apply a complete desired module set in one shot.

    POST /modules/apply/
    Body: {"modules": ["risk", "dsb", "gbu"], "plan_code": "business"}

    Activates listed modules, deactivates the rest.
    Returns JSON: {"activated": [...], "deactivated": [...]}
    """

    def post(self, request: HttpRequest) -> HttpResponse:
        org = _get_org(request)
        if not org:
            return JsonResponse({"error": "No tenant context"}, status=403)

        try:
            data = json.loads(request.body)
            desired = set(data.get("modules", []))
            plan_code = str(data.get("plan_code", "business"))
        except (ValueError, json.JSONDecodeError):
            return JsonResponse({"error": "Invalid request body"}, status=400)

        # Validate all module codes
        catalogue = get_catalogue()
        unknown = desired - set(catalogue.keys())
        if unknown:
            return JsonResponse({"error": f"Unknown modules: {unknown}"}, status=400)

        result = apply_module_set(org, desired, plan_code=plan_code)
        return JsonResponse(result)


class ModuleStatusView(LoginRequiredMixin, View):
    """JSON API: current active modules for the tenant.

    GET /modules/status/
    Returns: {"active": ["risk", "dsb"], "all": ["risk", "dsb", "gbu", ...]}
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        active = get_active_modules(tenant_id) if tenant_id else set()
        return JsonResponse(
            {
                "active": sorted(active),
                "all": sorted(get_catalogue().keys()),
            }
        )
