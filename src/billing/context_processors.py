"""Billing context processor — injects stripe_sub into every template context."""

from __future__ import annotations

import logging

from django.http import HttpRequest

logger = logging.getLogger(__name__)


def billing_context(request: HttpRequest) -> dict:
    """Add current StripeSubscription to template context.

    Returns {'stripe_sub': StripeSubscription | None}.
    Safe to use on all pages (unauthenticated requests return None).
    """
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"stripe_sub": None}

    tenant_id = getattr(request, "tenant_id", None)
    if not tenant_id:
        return {"stripe_sub": None}

    try:
        from tenancy.models import Organization
        from billing.models import StripeSubscription

        org = Organization.objects.filter(tenant_id=tenant_id).first()
        if not org:
            return {"stripe_sub": None}

        sub = (
            StripeSubscription.objects.filter(organization=org)
            .exclude(status="canceled")
            .order_by("-created_at")
            .first()
        )
        return {"stripe_sub": sub}
    except Exception:
        logger.exception("[billing] context_processor error for tenant=%s", tenant_id)
        return {"stripe_sub": None}
