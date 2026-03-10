"""Internal billing API — called by billing-hub after Stripe checkout.

Authentication: X-Billing-Secret header must match BILLING_INTERNAL_SECRET setting.
ADR-118: Platform Store — billing-hub als zentraler Registrierungs- und Zahlungspunkt.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.utils import timezone
from ninja import Router, Schema
from ninja.security import HttpBearer

from billing.services import activate_subscription, suspend_subscription
from tenancy.models import Membership, Organization

logger = logging.getLogger(__name__)

User = get_user_model()


class BillingInternalAuth(HttpBearer):
    """Validates X-Billing-Secret header against BILLING_INTERNAL_SECRET setting."""

    openapi_scheme = "bearer"

    def authenticate(self, request: HttpRequest, token: str) -> str | None:
        expected = getattr(settings, "BILLING_INTERNAL_SECRET", "")
        if not expected:
            logger.error("[internal_api] BILLING_INTERNAL_SECRET not configured")
            return None
        if token == expected:
            return token
        logger.warning("[internal_api] Invalid BILLING_INTERNAL_SECRET attempt")
        return None


class ActivatePayload(Schema):
    tenant_id: uuid.UUID
    email: str
    plan: str
    modules: list[str] = []
    trial_ends_at: Optional[datetime] = None


class DeactivatePayload(Schema):
    tenant_id: uuid.UUID


class ActivateResponse(Schema):
    status: str
    tenant_id: str
    org_created: bool
    user_created: bool


class DeactivateResponse(Schema):
    status: str
    tenant_id: str


router = Router(auth=BillingInternalAuth(), tags=["internal"])


@router.post("/activate", response=ActivateResponse)
def activate(request: HttpRequest, payload: ActivatePayload) -> ActivateResponse:
    """Create or update Tenant + User, then activate plan modules.

    Called by billing-hub after:
    - Stripe checkout.session.completed
    - Trial start
    """
    tenant_id = payload.tenant_id
    org_created = False
    user_created = False

    org, org_created = Organization.objects.get_or_create(
        tenant_id=tenant_id,
        defaults={
            "slug": str(tenant_id)[:8],
            "name": payload.email.split("@")[0],
            "status": Organization.Status.TRIAL,
            "plan_code": payload.plan,
            "trial_ends_at": payload.trial_ends_at,
        },
    )

    if not org_created:
        org.plan_code = payload.plan
        org.status = Organization.Status.ACTIVE
        if payload.trial_ends_at:
            org.trial_ends_at = payload.trial_ends_at
        org.save(update_fields=["plan_code", "status", "trial_ends_at", "updated_at"])

    user, user_created = User.objects.get_or_create(
        email=payload.email,
        defaults={
            "username": payload.email,
            "is_active": True,
        },
    )

    Membership.objects.get_or_create(
        tenant_id=tenant_id,
        user=user,
        defaults={
            "organization": org,
            "role": Membership.Role.OWNER,
            "accepted_at": timezone.now(),
        },
    )

    activate_subscription(
        organization=org,
        plan_code=payload.plan,
        stripe_subscription_id="",
        stripe_price_id="",
    )

    logger.info(
        "[internal_api] activate: tenant=%s plan=%s org_created=%s user_created=%s",
        tenant_id,
        payload.plan,
        org_created,
        user_created,
    )

    return ActivateResponse(
        status="activated",
        tenant_id=str(tenant_id),
        org_created=org_created,
        user_created=user_created,
    )


@router.post("/deactivate", response=DeactivateResponse)
def deactivate(request: HttpRequest, payload: DeactivatePayload) -> DeactivateResponse:
    """Suspend all active modules for a tenant.

    Called by billing-hub after:
    - Trial expiry
    - Stripe subscription.deleted / payment failure
    """
    tenant_id = payload.tenant_id
    try:
        org = Organization.objects.get(tenant_id=tenant_id)
    except Organization.DoesNotExist:
        logger.warning("[internal_api] deactivate: tenant=%s not found", tenant_id)
        return DeactivateResponse(status="not_found", tenant_id=str(tenant_id))

    suspend_subscription(org)
    org.status = Organization.Status.SUSPENDED
    org.suspended_at = timezone.now()
    org.save(update_fields=["status", "suspended_at", "updated_at"])

    logger.info("[internal_api] deactivate: tenant=%s suspended", tenant_id)
    return DeactivateResponse(status="suspended", tenant_id=str(tenant_id))
