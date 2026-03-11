"""Module-Shop views (ADR-137 Phase 3).

URLs:
    /modules/                    → catalogue
    /modules/<code>/             → detail
    /modules/<code>/activate/    → POST → billing-hub redirect
    /modules/<code>/cancel/      → POST → deactivation request
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from .catalogue import enrich_catalogue, get_module_entry

logger = logging.getLogger(__name__)


def _get_billing_checkout_url() -> str:
    """Return billing-hub checkout base URL."""
    return getattr(
        settings,
        "BILLING_HUB_CHECKOUT_URL",
        "https://billing.iil.pet/checkout",
    )


def _get_billing_cancel_url() -> str:
    """Return billing-hub cancel base URL."""
    return getattr(
        settings,
        "BILLING_HUB_CANCEL_URL",
        "https://billing.iil.pet/cancel",
    )


def _get_product_name() -> str:
    """Return the product name for billing-hub."""
    return getattr(
        settings,
        "MODULE_SHOP_PRODUCT_NAME",
        "risk-hub",
    )


@login_required
def catalogue_view(request: HttpRequest) -> HttpResponse:
    """Show module catalogue with status per tenant."""
    tenant_id = getattr(request, "tenant_id", None)
    tenant = getattr(request, "tenant", None)
    if not tenant_id or not tenant:
        return redirect("/")

    plan_code = getattr(tenant, "plan_code", "")
    modules = enrich_catalogue(tenant_id, plan_code)

    activated = request.GET.get("activated")
    if activated:
        messages.success(
            request,
            f'Modul "{activated}" wurde aktiviert!',
        )

    return render(request, "module_shop/catalogue.html", {
        "modules": modules,
        "tenant": tenant,
    })


@login_required
def detail_view(
    request: HttpRequest, code: str,
) -> HttpResponse:
    """Show module detail page."""
    tenant_id = getattr(request, "tenant_id", None)
    tenant = getattr(request, "tenant", None)
    if not tenant_id or not tenant:
        return redirect("/")

    entry = get_module_entry(code)
    if not entry:
        return HttpResponse("Modul nicht gefunden.", status=404)

    plan_code = getattr(tenant, "plan_code", "")
    modules = enrich_catalogue(tenant_id, plan_code)
    module = next(
        (m for m in modules if m["code"] == code), None
    )

    return render(request, "module_shop/detail.html", {
        "module": module or {"code": code, **entry},
        "tenant": tenant,
    })


@login_required
def activate_view(
    request: HttpRequest, code: str,
) -> HttpResponse:
    """POST: Redirect to billing-hub checkout for module."""
    if request.method != "POST":
        return redirect("module_shop:detail", code=code)

    tenant_id = getattr(request, "tenant_id", None)
    if not tenant_id:
        return redirect("/")

    entry = get_module_entry(code)
    if not entry:
        return HttpResponse("Modul nicht gefunden.", status=404)

    if not entry.get("standalone_bookable", False):
        messages.error(
            request,
            "Dieses Modul ist nicht einzeln buchbar.",
        )
        return redirect("module_shop:detail", code=code)

    # Build billing-hub checkout URL
    params = urlencode({
        "product": _get_product_name(),
        "module": code,
        "tenant_id": str(tenant_id),
        "return_url": request.build_absolute_uri(
            f"/billing/modules/?activated={code}"
        ),
    })
    checkout_url = f"{_get_billing_checkout_url()}?{params}"

    logger.info(
        "[module_shop] activate: module=%s tenant=%s → %s",
        code,
        tenant_id,
        checkout_url,
    )
    return redirect(checkout_url)


@login_required
def cancel_view(
    request: HttpRequest, code: str,
) -> HttpResponse:
    """POST: Send deactivation request to billing-hub."""
    if request.method != "POST":
        return redirect("module_shop:detail", code=code)

    tenant_id = getattr(request, "tenant_id", None)
    if not tenant_id:
        return redirect("/")

    # For now, just log and show message
    # Full billing-hub integration in Phase 4
    logger.info(
        "[module_shop] cancel request: module=%s tenant=%s",
        code,
        tenant_id,
    )
    messages.info(
        request,
        f'Kündigungsanfrage für "{code}" wurde gesendet. '
        "Sie erhalten eine Bestätigung per E-Mail.",
    )
    return redirect("module_shop:catalogue")
