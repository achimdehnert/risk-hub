"""Plan → Module mapping and Stripe price IDs (read from settings/env)."""

from django.conf import settings

PLAN_MODULES: dict[str, list[str]] = {
    "starter": ["gbu"],
    "professional": ["risk", "dsb", "gbu", "actions", "documents"],
    "business": ["risk", "ex", "substances", "dsb", "gbu", "documents", "actions"],
    "enterprise": ["risk", "ex", "substances", "dsb", "gbu", "documents", "actions"],
}


def get_price_id(plan: str, billing: str = "monthly") -> str:
    """Return the Stripe Price ID for a given plan and billing period."""
    key = f"STRIPE_PRICE_{plan.upper()}_{billing.upper()}"
    return getattr(settings, key, "")
