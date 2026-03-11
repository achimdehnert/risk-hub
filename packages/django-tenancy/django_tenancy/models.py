"""Backward-compatible re-exports for Organization and Membership.

Concrete models are owned by the consuming app's ``tenancy`` module.
This module provides lazy imports so that existing code like
``from django_tenancy.models import Organization`` continues to work.

ModuleSubscription and ModuleMembership live in ``django_tenancy.module_models``.
"""

from __future__ import annotations


def get_organization_model():
    """Return the concrete Organization model (from settings.TENANT_MODEL)."""
    from django.apps import apps
    from django.conf import settings

    return apps.get_model(settings.TENANT_MODEL)


def get_membership_model():
    """Return the concrete Membership model."""
    from django.apps import apps

    return apps.get_model("tenancy", "Membership")


def __getattr__(name: str):
    if name == "Organization":
        return get_organization_model()
    if name == "Membership":
        return get_membership_model()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
