"""Tenancy component inclusion tags (ADR-041)."""

from django import template

register = template.Library()

MODULE_META = {
    "risk": {
        "label": "Risikobewertung",
        "icon": "shield-alert",
        "color": "orange",
        "url_prefix": "/risk/",
    },
    "dsb": {
        "label": "Datenschutz",
        "icon": "lock",
        "color": "blue",
        "url_prefix": "/dsb/",
    },
    "ex": {
        "label": "Explosionsschutz",
        "icon": "flame",
        "color": "red",
        "url_prefix": "/ex/",
    },
    "substances": {
        "label": "Gefahrstoffe",
        "icon": "flask-conical",
        "color": "purple",
        "url_prefix": "/substances/",
    },
}


@register.inclusion_tag("tenancy/components/_status_badge.html")
def org_status_badge(org):
    """Render colored status badge for an Organization."""
    return {"org": org}


@register.inclusion_tag("tenancy/components/_module_subscription_card.html")
def module_subscription_card(subscription, org):
    """Render a module subscription card with status + actions."""
    meta = MODULE_META.get(subscription.module, {
        "label": subscription.module.upper(),
        "icon": "box",
        "color": "gray",
        "url_prefix": f"/{subscription.module}/",
    })
    return {"sub": subscription, "org": org, "meta": meta}


@register.inclusion_tag("tenancy/components/_module_membership_row.html")
def module_membership_row(membership, org):
    """Render a table row for a ModuleMembership."""
    return {"mm": membership, "org": org}


@register.inclusion_tag("tenancy/components/_member_row.html")
def member_row(membership, org):
    """Render a table row for an org Membership."""
    return {"m": membership, "org": org}


@register.simple_tag
def module_label(module_code):
    """Return human-readable module label."""
    return MODULE_META.get(module_code, {}).get("label", module_code.upper())


@register.simple_tag
def module_icon(module_code):
    """Return lucide icon name for a module."""
    return MODULE_META.get(module_code, {}).get("icon", "box")


@register.simple_tag
def module_color(module_code):
    """Return tailwind color key for a module."""
    return MODULE_META.get(module_code, {}).get("color", "gray")
