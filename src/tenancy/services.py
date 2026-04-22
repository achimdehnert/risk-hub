"""Tenancy query helpers (ADR-041)."""

from __future__ import annotations

from django.db.models import Count


def get_all_organizations():
    """Return all Organizations ordered by name."""
    from tenancy.models import Organization

    return Organization.objects.all().order_by("name")


def get_org_member_counts():
    """Return dict of {tenant_id: member_count} for all orgs."""
    from tenancy.models import Membership

    return dict(
        Membership.objects.values_list("tenant_id")
        .annotate(cnt=Count("id"))
        .values_list("tenant_id", "cnt")
    )


def get_org_module_counts():
    """Return dict of {tenant_id: module_count} for active/trial subscriptions."""
    from django_tenancy.module_models import ModuleSubscription

    return dict(
        ModuleSubscription.objects.filter(status__in=["trial", "active"])
        .values_list("tenant_id")
        .annotate(cnt=Count("id"))
        .values_list("tenant_id", "cnt")
    )


def get_module_subscription_stats() -> dict:
    """Return platform-wide module subscription stats."""
    from django_tenancy.module_models import ModuleSubscription

    return {
        "active_modules": ModuleSubscription.objects.filter(status="active").count(),
        "trial_modules": ModuleSubscription.objects.filter(status="trial").count(),
    }


def get_org_memberships(tenant_id):
    """Return Memberships for an org with user + role prefetched."""
    from tenancy.models import Membership

    return Membership.objects.filter(tenant_id=tenant_id).select_related("user")


def get_org_roles(tenant_id):
    """Return Roles available for an org."""
    from permissions.models import Role

    return Role.objects.filter(tenant_id=tenant_id).order_by("name")


def get_org_subscriptions(tenant_id):
    """Return ModuleSubscriptions for an org ordered by module."""
    from django_tenancy.module_models import ModuleSubscription

    return ModuleSubscription.objects.filter(tenant_id=tenant_id).order_by("module")


def create_user(username: str, email: str, password: str, **kwargs):
    """Create and return a new User."""
    from identity.models import User

    return User.objects.create_user(username=username, email=email, password=password, **kwargs)


def create_membership(user, tenant_id):
    """Create and return a new Membership."""
    from tenancy.models import Membership

    return Membership.objects.create(user=user, tenant_id=tenant_id)


def get_module_memberships(tenant_id, module: str):
    """Return ModuleMemberships for tenant + module."""
    from django_tenancy.module_models import ModuleMembership

    return ModuleMembership.objects.filter(tenant_id=tenant_id, module=module)


def get_or_create_module_subscription(tenant_id, module: str) -> tuple:
    """Get or create ModuleSubscription for tenant + module."""
    from django_tenancy.module_models import ModuleSubscription

    return ModuleSubscription.objects.update_or_create(
        tenant_id=tenant_id,
        module=module,
        defaults={"status": "active"},
    )


def subscription_exists(tenant_id, module: str) -> bool:
    """Return True if an active/trial subscription exists."""
    from django_tenancy.module_models import ModuleSubscription

    return ModuleSubscription.objects.filter(
        tenant_id=tenant_id,
        module=module,
        status__in=["trial", "active"],
    ).exists()


def create_module_subscription(tenant_id, module: str, status: str = "trial"):
    """Create a new ModuleSubscription."""
    from django_tenancy.module_models import ModuleSubscription

    return ModuleSubscription.objects.create(
        tenant_id=tenant_id,
        module=module,
        status=status,
    )


def get_organization_by_tenant(tenant_id):
    """Return Organization for a tenant_id, or None."""
    from tenancy.models import Organization

    return Organization.objects.filter(tenant_id=tenant_id).first()
