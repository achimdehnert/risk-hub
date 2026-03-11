"""Internal billing API — called by billing-hub after Stripe checkout.

Authentication: HMAC-SHA256 signature via X-Billing-Timestamp + X-Billing-Signature.
ADR-118: Platform Store — billing-hub als zentraler Registrierungs- und Zahlungspunkt.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
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

HMAC_REPLAY_WINDOW = 300  # 5 minutes


def _verify_hmac(request: HttpRequest, secret: str) -> bool:
    """Verify HMAC-SHA256 signature. Returns True if valid."""
    timestamp = request.headers.get("X-Billing-Timestamp", "")
    signature = request.headers.get("X-Billing-Signature", "")
    if not timestamp or not signature:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(time.time() - ts) > HMAC_REPLAY_WINDOW:
        logger.warning("[internal_api] HMAC timestamp outside replay window")
        return False
    try:
        body = request.body.decode("utf-8")
    except Exception:
        body = ""
    payload_str = f"{timestamp}:{body}"
    expected = hmac.new(
        secret.encode(),
        payload_str.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


class BillingHmacAuth(HttpBearer):
    """HMAC-SHA256 auth — validates X-Billing-Timestamp + X-Billing-Signature.

    Supports dual-secret rotation: BILLING_HMAC_SECRET (primary) and
    BILLING_HMAC_SECRET_PREV (previous, optional).
    """

    openapi_scheme = "bearer"

    def authenticate(self, request: HttpRequest, token: str) -> str | None:
        primary = getattr(settings, "BILLING_HMAC_SECRET", "")
        if not primary:
            logger.error("[internal_api] BILLING_HMAC_SECRET not configured")
            return None
        if _verify_hmac(request, primary):
            return "hmac-ok"
        prev = getattr(settings, "BILLING_HMAC_SECRET_PREV", "")
        if prev and _verify_hmac(request, prev):
            logger.info("[internal_api] Auth via previous HMAC secret (rotation)")
            return "hmac-ok-prev"
        logger.warning("[internal_api] HMAC verification failed")
        return None


class ActivatePayload(Schema):
    tenant_id: uuid.UUID
    email: str
    plan: str
    modules: list[str] = []
    trial_ends_at: Optional[datetime] = None


class DeactivatePayload(Schema):
    tenant_id: uuid.UUID
    reason: str = ""


class ActivateResponse(Schema):
    status: str
    tenant_id: str
    org_created: bool
    user_created: bool


class DeactivateResponse(Schema):
    status: str
    tenant_id: str


router = Router(auth=BillingHmacAuth(), tags=["internal"])


@router.post("/activate", response=ActivateResponse)
def activate(request: HttpRequest, payload: ActivatePayload) -> ActivateResponse:
    """Create or update Tenant + User, then activate plan modules.

    Called by billing-hub after:
    - Stripe checkout.session.completed
    - Trial start

    Idempotent: safe to call multiple times.
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
            "is_readonly": False,
        },
    )

    if not org_created:
        org.plan_code = payload.plan
        org.status = Organization.Status.ACTIVE
        org.is_readonly = False
        org.deactivation_reason = ""
        if payload.trial_ends_at:
            org.trial_ends_at = payload.trial_ends_at
        org.save(
            update_fields=[
                "plan_code",
                "status",
                "trial_ends_at",
                "is_readonly",
                "deactivation_reason",
                "updated_at",
            ]
        )

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
def deactivate(
    request: HttpRequest, payload: DeactivatePayload
) -> DeactivateResponse:
    """Suspend all active modules for a tenant. Set read-only + GDPR delete date.

    Called by billing-hub after:
    - Trial expiry
    - Stripe subscription.deleted / payment failure

    GDPR: org is scheduled for hard-delete 90 days after deactivation.
    """
    tenant_id = payload.tenant_id
    try:
        org = Organization.objects.get(tenant_id=tenant_id)
    except Organization.DoesNotExist:
        logger.warning(
            "[internal_api] deactivate: tenant=%s not found", tenant_id
        )
        return DeactivateResponse(status="not_found", tenant_id=str(tenant_id))

    suspend_subscription(org)

    now = timezone.now()
    from datetime import timedelta
    org.status = Organization.Status.SUSPENDED
    org.suspended_at = now
    org.is_readonly = True
    org.deactivation_reason = payload.reason or "billing-hub: subscription ended"
    org.gdpr_delete_at = now + timedelta(days=90)
    org.save(
        update_fields=[
            "status",
            "suspended_at",
            "is_readonly",
            "deactivation_reason",
            "gdpr_delete_at",
            "updated_at",
        ]
    )

    logger.info(
        "[internal_api] deactivate: tenant=%s suspended, gdpr_delete_at=%s",
        tenant_id,
        org.gdpr_delete_at,
    )
    return DeactivateResponse(status="suspended", tenant_id=str(tenant_id))
