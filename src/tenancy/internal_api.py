"""Internal billing API — called by billing-hub after Stripe checkout (ADR-118).

Authentication: HMAC-SHA256 via X-Billing-Timestamp + X-Billing-Signature.
Moved from billing/ to tenancy/ after ADR-137 Phase 4.3.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.utils import timezone
from django.utils.text import slugify
from ninja import Router, Schema
from ninja.security import HttpBearer

from tenancy.models import Membership, Organization

logger = logging.getLogger(__name__)

User = get_user_model()

HMAC_REPLAY_WINDOW = 300  # 5 minutes
GDPR_DELETE_DAYS = 90


def _verify_hmac(request: HttpRequest, secret: str) -> bool:
    """Verify HMAC-SHA256 signature. Returns True if valid."""
    ts_header = request.headers.get("X-Billing-Timestamp", "")
    sig_header = request.headers.get("X-Billing-Signature", "")
    if not ts_header or not sig_header:
        return False
    try:
        ts = int(ts_header)
    except ValueError:
        return False
    if abs(time.time() - ts) > HMAC_REPLAY_WINDOW:
        logger.warning("[internal_api] HMAC timestamp outside replay window")
        return False
    try:
        body = request.body.decode("utf-8")
    except Exception:
        body = ""
    expected = hmac.new(
        secret.encode(),
        f"{ts_header}.{body}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, sig_header)


class BillingHmacAuth(HttpBearer):
    """HMAC-SHA256 auth with dual-secret rotation support."""

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


# ── Schemas ──────────────────────────────────────────────


class ActivatePayload(Schema):
    tenant_id: uuid.UUID
    email: str
    plan: str
    modules: list[str] = []
    trial_ends_at: str | None = None


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


# ── Router ───────────────────────────────────────────────

router = Router(auth=BillingHmacAuth(), tags=["internal"])


@router.post("/activate", response=ActivateResponse)
def activate(request: HttpRequest, payload: ActivatePayload):
    """Create or reactivate tenant + user. Idempotent."""
    tenant_id = payload.tenant_id

    org, org_created = Organization.objects.get_or_create(
        tenant_id=tenant_id,
        defaults={
            "slug": _unique_slug(payload.email),
            "name": payload.email.split("@")[0],
            "status": Organization.Status.TRIAL
            if payload.trial_ends_at
            else Organization.Status.ACTIVE,
            "plan_code": payload.plan,
            "is_readonly": False,
        },
    )

    if not org_created:
        org.plan_code = payload.plan
        org.status = Organization.Status.ACTIVE
        org.is_readonly = False
        org.deactivation_reason = ""
        org.gdpr_delete_at = None
        if payload.trial_ends_at:
            org.trial_ends_at = timezone.datetime.fromisoformat(payload.trial_ends_at)
            org.status = Organization.Status.TRIAL
        org.save(
            update_fields=[
                "plan_code",
                "status",
                "trial_ends_at",
                "is_readonly",
                "deactivation_reason",
                "gdpr_delete_at",
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

    _sync_modules(org, payload.plan, payload.modules)

    logger.info(
        "[internal_api] activate: tenant=%s plan=%s org=%s user=%s",
        tenant_id,
        payload.plan,
        "created" if org_created else "updated",
        "created" if user_created else "exists",
    )

    return ActivateResponse(
        status="activated",
        tenant_id=str(tenant_id),
        org_created=org_created,
        user_created=user_created,
    )


@router.post("/deactivate", response=DeactivateResponse)
def deactivate(request: HttpRequest, payload: DeactivatePayload):
    """Suspend tenant, set read-only + GDPR delete schedule."""
    tenant_id = payload.tenant_id
    try:
        org = Organization.objects.get(tenant_id=tenant_id)
    except Organization.DoesNotExist:
        logger.warning("[internal_api] deactivate: tenant=%s not found", tenant_id)
        return DeactivateResponse(status="not_found", tenant_id=str(tenant_id))

    now = timezone.now()
    reason = payload.reason or "billing-hub: subscription ended"
    org.status = Organization.Status.SUSPENDED
    org.suspended_at = now
    org.is_readonly = True
    org.deactivation_reason = reason
    org.gdpr_delete_at = now + timedelta(days=GDPR_DELETE_DAYS)
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
        "[internal_api] deactivate: tenant=%s reason=%s gdpr=%s",
        tenant_id,
        reason,
        org.gdpr_delete_at,
    )
    return DeactivateResponse(status="suspended", tenant_id=str(tenant_id))


# ── Helpers ──────────────────────────────────────────────


def _unique_slug(email: str) -> str:
    """Generate a unique slug from email prefix."""
    base = slugify(email.split("@")[0])[:50] or "org"
    slug = base
    counter = 1
    while Organization.objects.filter(slug=slug).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def _sync_modules(org: Organization, plan: str, modules: list[str]) -> None:
    """Create/update ModuleSubscriptions if django_tenancy is available."""
    try:
        from django_tenancy.module_models import ModuleSubscription

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
    except ImportError:
        logger.debug("[internal_api] django_tenancy not available, skip module sync")
