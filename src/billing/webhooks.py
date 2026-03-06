"""Stripe webhook event handlers."""

from __future__ import annotations

import logging

from django_tenancy.models import Organization

from billing.models import BillingEvent
from billing.services import activate_subscription, suspend_subscription, sync_subscription_from_stripe

logger = logging.getLogger(__name__)


def _get_organization(tenant_id: str) -> Organization | None:
    try:
        return Organization.objects.get(tenant_id=tenant_id)
    except Organization.DoesNotExist:
        logger.warning("[billing] Organization not found for tenant_id=%s", tenant_id)
        return None


def handle_checkout_session_completed(event: dict) -> None:
    """Activate modules when a checkout is successfully completed."""
    session = event["data"]["object"]
    if session.get("mode") != "subscription":
        return

    subscription_id = session.get("subscription")
    metadata = session.get("subscription_data", {}).get("metadata") or session.get("metadata", {})
    tenant_id = metadata.get("tenant_id")
    plan_code = metadata.get("plan_code", "")

    if not tenant_id or not subscription_id:
        logger.warning("[billing] checkout.session.completed missing tenant_id or subscription_id")
        return

    org = _get_organization(tenant_id)
    if not org:
        return

    activate_subscription(org, plan_code, subscription_id, "")
    logger.info("[billing] checkout.session.completed processed for tenant=%s", tenant_id)


def handle_subscription_updated(event: dict) -> None:
    """Sync subscription state and activate/suspend modules accordingly."""
    sub = event["data"]["object"]
    tenant_id = sub.get("metadata", {}).get("tenant_id")
    plan_code = sub.get("metadata", {}).get("plan_code", "")

    if not tenant_id:
        logger.warning("[billing] subscription updated event missing tenant_id in metadata")
        return

    org = _get_organization(tenant_id)
    if not org:
        return

    sync_subscription_from_stripe(sub, org)

    if sub["status"] in ("active", "trialing"):
        activate_subscription(org, plan_code, sub["id"], "")
    elif sub["status"] in ("past_due", "unpaid", "canceled"):
        suspend_subscription(org)

    logger.info(
        "[billing] subscription.updated tenant=%s status=%s", tenant_id, sub["status"]
    )


def handle_subscription_deleted(event: dict) -> None:
    """Suspend all modules when a subscription is deleted/cancelled."""
    sub = event["data"]["object"]
    tenant_id = sub.get("metadata", {}).get("tenant_id")

    if not tenant_id:
        logger.warning("[billing] subscription.deleted missing tenant_id")
        return

    org = _get_organization(tenant_id)
    if not org:
        return

    suspend_subscription(org)
    sync_subscription_from_stripe(sub, org)
    logger.info("[billing] subscription.deleted: modules suspended for tenant=%s", tenant_id)


def handle_invoice_payment_failed(event: dict) -> None:
    """Log payment failures — grace period handled by Stripe dunning settings."""
    invoice = event["data"]["object"]
    customer_id = invoice.get("customer")
    attempt = invoice.get("attempt_count", 0)
    logger.warning(
        "[billing] invoice.payment_failed customer=%s attempt=%d", customer_id, attempt
    )


def handle_invoice_payment_succeeded(event: dict) -> None:
    """Update current_period_end after successful payment."""
    invoice = event["data"]["object"]
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return
    from billing.models import StripeSubscription
    from django.utils import timezone

    period_end = invoice.get("lines", {}).get("data", [{}])[0].get("period", {}).get("end")
    if period_end:
        StripeSubscription.objects.filter(stripe_subscription_id=subscription_id).update(
            current_period_end=timezone.datetime.fromtimestamp(period_end, tz=timezone.utc)
        )
        logger.info("[billing] invoice.payment_succeeded subscription=%s", subscription_id)


EVENT_HANDLERS = {
    "checkout.session.completed": handle_checkout_session_completed,
    "customer.subscription.updated": handle_subscription_updated,
    "customer.subscription.deleted": handle_subscription_deleted,
    "invoice.payment_failed": handle_invoice_payment_failed,
    "invoice.payment_succeeded": handle_invoice_payment_succeeded,
}
