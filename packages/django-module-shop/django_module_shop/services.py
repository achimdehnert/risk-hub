"""Service layer for module subscription management.

Provides the business logic for activating, deactivating, and querying
module subscriptions for a tenant. Views should call these functions,
never touching ModuleSubscription directly.

All functions accept tenant_id (UUID) + organization instance to avoid
redundant DB lookups.
"""

from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def get_active_modules(tenant_id: UUID) -> set[str]:
    """Return set of active module codes for a tenant."""
    from django_tenancy.module_models import ModuleSubscription

    return set(
        ModuleSubscription.objects.filter(
            tenant_id=tenant_id,
            status__in=[
                ModuleSubscription.Status.ACTIVE,
                ModuleSubscription.Status.TRIAL,
            ],
        ).values_list("module", flat=True)
    )


def get_subscription_map(tenant_id: UUID) -> dict:
    """Return {module_code: subscription} for all subscriptions of a tenant."""
    from django_tenancy.module_models import ModuleSubscription

    return {sub.module: sub for sub in ModuleSubscription.objects.filter(tenant_id=tenant_id)}


def activate_module(organization, module_code: str, plan_code: str = "business"):
    """Activate a module for a tenant (create or re-activate).

    Args:
        organization: Organization instance.
        module_code:  Module code to activate.
        plan_code:    Billing plan identifier (default "business").

    Returns:
        The created or updated ModuleSubscription.
    """
    from django_tenancy.module_models import ModuleSubscription

    sub, created = ModuleSubscription.objects.get_or_create(
        tenant_id=organization.tenant_id,
        module=module_code,
        defaults={
            "organization": organization,
            "status": ModuleSubscription.Status.ACTIVE,
            "plan_code": plan_code,
        },
    )
    if not created and sub.status != ModuleSubscription.Status.ACTIVE:
        sub.status = ModuleSubscription.Status.ACTIVE
        sub.plan_code = plan_code
        sub.save(update_fields=["status", "plan_code", "updated_at"])
        logger.info(
            "[module-shop] re-activated module=%s tenant=%s",
            module_code,
            organization.tenant_id,
        )
    elif created:
        logger.info(
            "[module-shop] activated module=%s tenant=%s",
            module_code,
            organization.tenant_id,
        )
    return sub


def deactivate_module(organization, module_code: str) -> bool:
    """Suspend a module subscription. Returns True if found and updated.

    Args:
        organization: Organization instance.
        module_code:  Module code to deactivate.

    Returns:
        True if subscription was found and suspended, False otherwise.
    """
    from django_tenancy.module_models import ModuleSubscription

    updated = ModuleSubscription.objects.filter(
        tenant_id=organization.tenant_id,
        module=module_code,
        status__in=[ModuleSubscription.Status.ACTIVE, ModuleSubscription.Status.TRIAL],
    ).update(status=ModuleSubscription.Status.SUSPENDED)

    if updated:
        logger.info(
            "[module-shop] deactivated module=%s tenant=%s",
            module_code,
            organization.tenant_id,
        )
    return bool(updated)


def apply_module_set(
    organization,
    desired_modules: set[str],
    plan_code: str = "business",
) -> dict[str, list[str]]:
    """Reconcile the tenant's active modules with the desired set.

    Activates modules that are in desired but not yet active.
    Suspends modules that are currently active but not in desired.

    Args:
        organization:    Organization instance.
        desired_modules: Set of module codes that should be active.
        plan_code:       Plan code to use for newly activated modules.

    Returns:
        {"activated": [...], "deactivated": [...]} — lists of affected codes.
    """
    current = get_active_modules(organization.tenant_id)
    to_activate = desired_modules - current
    to_deactivate = current - desired_modules

    for code in to_activate:
        activate_module(organization, code, plan_code=plan_code)

    for code in to_deactivate:
        deactivate_module(organization, code)

    return {
        "activated": sorted(to_activate),
        "deactivated": sorted(to_deactivate),
    }
