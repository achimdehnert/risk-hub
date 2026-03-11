"""Module catalogue utilities (ADR-137 Phase 3).

Reads MODULE_SHOP_CATALOGUE from Django settings and enriches
each entry with the tenant's current subscription status.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

# Default catalogue — apps override via settings
DEFAULT_CATALOGUE: dict[str, dict[str, Any]] = {}


def get_catalogue() -> dict[str, dict[str, Any]]:
    """Return the module catalogue from settings."""
    return getattr(
        settings, "MODULE_SHOP_CATALOGUE", DEFAULT_CATALOGUE
    )


def get_module_entry(code: str) -> dict[str, Any] | None:
    """Return a single module entry or None."""
    return get_catalogue().get(code)


def enrich_catalogue(
    tenant_id,
    plan_code: str = "",
) -> list[dict[str, Any]]:
    """Enrich catalogue with tenant subscription status.

    Returns list of dicts with keys:
        code, name, description, icon, status,
        is_active, is_bookable, included_in_plan
    """
    from django_tenancy.module_models import ModuleSubscription

    catalogue = get_catalogue()
    if not catalogue:
        return []

    # Get active subscriptions for this tenant
    subs = {}
    try:
        for sub in ModuleSubscription.objects.filter(
            tenant_id=tenant_id,
        ).only("module", "status", "trial_ends_at", "expires_at"):
            subs[sub.module] = sub
    except Exception:
        logger.exception("Failed to load subscriptions")

    plan_modules = getattr(settings, "PLAN_MODULES", {})
    included = set(plan_modules.get(plan_code, []))

    result = []
    for code, meta in catalogue.items():
        sub = subs.get(code)
        if sub and sub.is_accessible:
            status = "active"
        elif code in included:
            status = "included"
        elif meta.get("standalone_bookable", False):
            status = "available"
        else:
            status = "locked"

        result.append({
            "code": code,
            "name": meta.get("name", code),
            "description": meta.get("description", ""),
            "icon": meta.get("icon", "package"),
            "trial_days": meta.get("trial_days", 0),
            "status": status,
            "is_active": status == "active",
            "is_bookable": status in (
                "available", "included",
            ),
            "included_in_plan": code in included,
            "subscription": sub,
        })

    # Sort: active first, then available, then locked
    order = {"active": 0, "included": 1, "available": 2, "locked": 3}
    result.sort(key=lambda m: order.get(m["status"], 9))
    return result
