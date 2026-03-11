"""Stripe billing service layer."""

from __future__ import annotations

import logging

import stripe
from django.conf import settings
from django.utils import timezone
from django_tenancy.module_models import ModuleSubscription

from billing.constants import PLAN_MODULES
from billing.models import StripeCustomer, StripeSubscription
from tenancy.models import Organization

logger = logging.getLogger(__name__)


def _stripe_client() -> stripe.Stripe:
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def get_or_create_customer(organization: Organization) -> str:
    """Return existing Stripe customer ID or create a new one."""
    try:
        return organization.stripe_customer.stripe_customer_id
    except StripeCustomer.DoesNotExist:
        pass

    client = _stripe_client()
    customer = client.Customer.create(
        name=organization.name,
        metadata={
            "tenant_id": str(organization.tenant_id),
            "org_id": str(organization.pk),
        },
    )
    StripeCustomer.objects.create(
        organization=organization,
        stripe_customer_id=customer["id"],
    )
    logger.info(
        "[billing] Created Stripe customer %s for org %s",
        customer["id"],
        organization.pk,
    )
    return customer["id"]


def create_checkout_session(
    organization: Organization,
    price_id: str,
    plan_code: str,
    success_url: str,
    cancel_url: str,
    trial_days: int = 14,
) -> str:
    """Create a Stripe Checkout Session and return the hosted URL."""
    client = _stripe_client()
    customer_id = get_or_create_customer(organization)

    session = client.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        subscription_data={
            "trial_period_days": trial_days,
            "metadata": {
                "plan_code": plan_code,
                "tenant_id": str(organization.tenant_id),
                "org_id": str(organization.pk),
            },
        },
        success_url=success_url,
        cancel_url=cancel_url,
        allow_promotion_codes=True,
    )
    logger.info(
        "[billing] Checkout session %s created for org %s plan=%s",
        session["id"],
        organization.pk,
        plan_code,
    )
    return session["url"]


def create_portal_session(organization: Organization, return_url: str) -> str:
    """Create a Stripe Customer Portal session URL."""
    client = _stripe_client()
    customer_id = get_or_create_customer(organization)
    session = client.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    logger.info("[billing] Portal session created for org %s", organization.pk)
    return session["url"]


def activate_subscription(
    organization: Organization,
    plan_code: str,
    stripe_subscription_id: str,
    stripe_price_id: str,
) -> None:
    """Activate ModuleSubscriptions for all modules included in the plan."""
    modules = PLAN_MODULES.get(plan_code, [])
    for module in modules:
        ModuleSubscription.objects.update_or_create(
            tenant_id=organization.tenant_id,
            module=module,
            defaults={
                "organization_id": organization.pk,
                "status": ModuleSubscription.Status.ACTIVE,
                "plan_code": plan_code,
                "activated_at": timezone.now(),
            },
        )
    logger.info(
        "[billing] Activated modules %s for org %s (plan=%s)",
        modules,
        organization.pk,
        plan_code,
    )


def suspend_subscription(organization: Organization) -> None:
    """Suspend all active ModuleSubscriptions for the organization."""
    updated = ModuleSubscription.objects.filter(
        tenant_id=organization.tenant_id,
        status=ModuleSubscription.Status.ACTIVE,
    ).update(status=ModuleSubscription.Status.SUSPENDED)
    logger.info("[billing] Suspended %d modules for org %s", updated, organization.pk)


def sync_subscription_from_stripe(
    stripe_subscription: dict,
    organization: Organization,
) -> None:
    """Sync a Stripe subscription object into StripeSubscription model."""
    plan_code = stripe_subscription.get("metadata", {}).get("plan_code", "")
    price_id = ""
    if stripe_subscription.get("items", {}).get("data"):
        price_id = stripe_subscription["items"]["data"][0]["price"]["id"]

    StripeSubscription.objects.update_or_create(
        stripe_subscription_id=stripe_subscription["id"],
        defaults={
            "organization": organization,
            "stripe_price_id": price_id,
            "plan_code": plan_code,
            "status": stripe_subscription["status"],
            "current_period_start": timezone.datetime.fromtimestamp(
                stripe_subscription["current_period_start"], tz=timezone.utc
            ),
            "current_period_end": timezone.datetime.fromtimestamp(
                stripe_subscription["current_period_end"], tz=timezone.utc
            ),
            "cancel_at_period_end": stripe_subscription.get("cancel_at_period_end", False),
            "canceled_at": (
                timezone.datetime.fromtimestamp(stripe_subscription["canceled_at"], tz=timezone.utc)
                if stripe_subscription.get("canceled_at")
                else None
            ),
        },
    )
    logger.info(
        "[billing] Synced subscription %s status=%s plan=%s",
        stripe_subscription["id"],
        stripe_subscription["status"],
        plan_code,
    )
