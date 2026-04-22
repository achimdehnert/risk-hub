"""Config app service layer (ADR-041).

Registration, tenant provisioning, and user lookup helpers.
Views must not call .create() / .filter().exists() directly.
"""

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# User lookups
# ---------------------------------------------------------------------------


def user_exists_by_username(username: str) -> bool:
    """Return True if a user with this username already exists."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.filter(username=username).exists()


def user_exists_by_email(email: str) -> bool:
    """Return True if a user with this email already exists."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.filter(email=email).exists()


def create_user(username: str, email: str, password: str):
    """Create and return a new User."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(username=username, email=email, password=password)


def get_organization_by_slug(slug: str):
    """Return Organization by slug, or None."""
    from tenancy.models import Organization

    return Organization.objects.filter(slug=slug).first()


# ---------------------------------------------------------------------------
# Tenant provisioning
# ---------------------------------------------------------------------------


def provision_trial_tenant(user, plan: str, modules_csv: str) -> None:
    """Create Organization + Membership + ModuleSubscriptions for a new trial user.

    Moved from config/views._provision_trial_tenant.
    """
    from django.utils import timezone
    from django_tenancy.module_models import ModuleMembership, ModuleSubscription

    from tenancy.models import Membership, Organization

    slug = user.username.lower().replace(" ", "-")[:50]
    base_slug = slug
    counter = 1
    while Organization.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    org = Organization.objects.create(
        name=user.username,
        slug=slug,
        status=Organization.Status.ACTIVE,
    )
    tenant_id = org.tenant_id

    user.tenant_id = tenant_id
    user.save(update_fields=["tenant_id"])

    Membership.objects.create(
        tenant_id=tenant_id,
        organization=org,
        user=user,
        role=Membership.Role.ADMIN,
        invited_by=user,
        invited_at=timezone.now(),
        accepted_at=timezone.now(),
    )

    from billing.constants import PLAN_MODULES

    plan_key = plan.lower() if plan else "professional"
    plan_modules = PLAN_MODULES.get(plan_key, PLAN_MODULES.get("professional", []))
    requested = [m.strip() for m in modules_csv.split(",") if m.strip()]
    active_modules = [m for m in plan_modules if not requested or m in requested]
    if not active_modules:
        active_modules = plan_modules

    for module in active_modules:
        ModuleSubscription.objects.update_or_create(
            tenant_id=tenant_id,
            module=module,
            defaults={
                "organization": org,
                "status": ModuleSubscription.Status.ACTIVE,
                "plan_code": plan_key,
                "activated_at": timezone.now(),
            },
        )
        ModuleMembership.objects.update_or_create(
            tenant_id=tenant_id,
            user=user,
            module=module,
            defaults={"role": ModuleMembership.Role.ADMIN},
        )

    logger.info("Provisioned trial tenant %s for user %s", org.slug, user.username)
