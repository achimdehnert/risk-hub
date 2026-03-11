"""Activation service for billing-hub internal API (ADR-118 Pilot).

Handles tenant creation/reactivation and deactivation triggered by billing-hub.
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from django_tenancy.module_models import ModuleSubscription

from tenancy.models import Membership, Organization

logger = logging.getLogger(__name__)

User = get_user_model()

GDPR_DELETE_DAYS = 90


def activate_tenant(
    *,
    tenant_id: str,
    email: str,
    plan: str,
    modules: list[str] | None = None,
    trial_ends_at: str | None = None,
) -> tuple[Organization, bool]:
    """Create or reactivate a tenant from billing-hub activate call.

    Returns (organization, created).
    Idempotent: re-call with same tenant_id returns existing org.
    """
    tid = uuid.UUID(tenant_id)
    modules = modules or []

    # Idempotent: check if org already exists
    try:
        org = Organization.objects.get(tenant_id=tid)
        created = False
        # Reactivate if previously deactivated
        if org.is_readonly or org.status == Organization.Status.SUSPENDED:
            org.status = (
                Organization.Status.ACTIVE if not trial_ends_at else Organization.Status.TRIAL
            )
            org.is_readonly = False
            org.deactivation_reason = ""
            org.gdpr_delete_at = None
            org.plan_code = plan
            if trial_ends_at:
                org.trial_ends_at = timezone.datetime.fromisoformat(trial_ends_at)
            org.save()
            logger.info("[activation] Reactivated org %s (tenant=%s)", org.pk, tid)
        else:
            logger.info("[activation] Org already active (tenant=%s), idempotent OK", tid)
        _sync_modules(org, plan, modules)
        return org, created
    except Organization.DoesNotExist:
        pass

    # Create new organization
    slug = slugify(email.split("@")[0])[:50] or "org"
    # Ensure unique slug
    base_slug = slug
    counter = 1
    while Organization.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    org = Organization.objects.create(
        tenant_id=tid,
        slug=slug,
        name=email.split("@")[0],
        status=Organization.Status.TRIAL if trial_ends_at else Organization.Status.ACTIVE,
        plan_code=plan,
        trial_ends_at=(timezone.datetime.fromisoformat(trial_ends_at) if trial_ends_at else None),
    )
    logger.info("[activation] Created org %s slug=%s (tenant=%s)", org.pk, slug, tid)

    # Create admin user with random password + owner membership
    user, user_created = User.objects.get_or_create(
        email=email,
        defaults={
            "username": email,
            "is_active": True,
        },
    )
    if user_created:
        user.set_password(get_random_string(32))
        user.save()
        logger.info("[activation] Created user %s", email)
        # TODO: Send "Set Password" email via django-allauth or custom flow

    Membership.objects.get_or_create(
        organization=org,
        user=user,
        defaults={
            "tenant_id": org.tenant_id,
            "role": Membership.Role.OWNER,
        },
    )

    _sync_modules(org, plan, modules)
    return org, True


def deactivate_tenant(
    *,
    tenant_id: str,
    reason: str = "cancelled",
) -> Organization | None:
    """Deactivate a tenant — set to read-only with GDPR delete schedule.

    Returns the organization or None if not found.
    """
    tid = uuid.UUID(tenant_id)
    try:
        org = Organization.objects.get(tenant_id=tid)
    except Organization.DoesNotExist:
        logger.warning("[activation] Deactivate: tenant %s not found", tid)
        return None

    org.is_readonly = True
    org.status = Organization.Status.SUSPENDED
    org.suspended_at = timezone.now()
    org.deactivation_reason = reason
    org.gdpr_delete_at = timezone.now() + timedelta(days=GDPR_DELETE_DAYS)
    org.save()

    # Suspend all active module subscriptions
    suspended = ModuleSubscription.objects.filter(
        tenant_id=org.tenant_id,
        status=ModuleSubscription.Status.ACTIVE,
    ).update(status=ModuleSubscription.Status.SUSPENDED)

    logger.info(
        "[activation] Deactivated org %s reason=%s, %d modules suspended, gdpr_delete=%s",
        org.pk,
        reason,
        suspended,
        org.gdpr_delete_at,
    )
    return org


def _sync_modules(org: Organization, plan: str, modules: list[str]) -> None:
    """Ensure ModuleSubscriptions exist for the given modules."""
    for module in modules:
        ModuleSubscription.objects.update_or_create(
            tenant_id=org.tenant_id,
            module=module,
            defaults={
                "organization_id": org.pk,
                "status": ModuleSubscription.Status.ACTIVE,
                "plan_code": plan,
                "activated_at": timezone.now(),
            },
        )
