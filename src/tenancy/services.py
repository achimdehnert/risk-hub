"""Tenancy query helpers (ADR-041)."""

from __future__ import annotations

import json
import logging

from django.db.models import Count

logger = logging.getLogger(__name__)


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


# ---------------------------------------------------------------------------
# Write helpers (ADR-041 Phase 3 — mutations)
# ---------------------------------------------------------------------------


def invite_user_to_org(org, form_data: dict, invited_by):
    """Create a new User and add them to an Organization as a Member.

    Returns (user, membership).
    """
    from django.utils import timezone

    from identity.models import User
    from tenancy.models import Membership

    user = User.objects.create_user(
        username=form_data["username"],
        email=form_data["email"],
        password=form_data["password"],
        first_name=form_data.get("first_name", ""),
        last_name=form_data.get("last_name", ""),
        tenant_id=org.tenant_id,
    )
    membership = Membership.objects.create(
        tenant_id=org.tenant_id,
        organization=org,
        user=user,
        role=form_data["role"],
        invited_by=invited_by,
        invited_at=timezone.now(),
        accepted_at=timezone.now(),
    )
    return user, membership


def add_module_subscription(org, module: str):
    """Create a TRIAL ModuleSubscription for an org + module.

    Returns the new ModuleSubscription.
    """
    from django_tenancy.module_models import ModuleSubscription

    return ModuleSubscription.objects.create(
        organization=org,
        tenant_id=org.tenant_id,
        module=module,
        status=ModuleSubscription.Status.TRIAL,
        plan_code="free",
    )


def grant_module_membership(org, user, module: str, role, granted_by, expires_at=None):
    """Create a ModuleMembership for user + module.

    Returns the new ModuleMembership.
    """
    from django_tenancy.module_models import ModuleMembership

    return ModuleMembership.objects.create(
        tenant_id=org.tenant_id,
        user=user,
        module=module,
        role=role,
        granted_by=granted_by,
        expires_at=expires_at,
    )


def ensure_role_assignment(user, org, membership_role: str) -> None:
    """Map a membership role to a system Role and create an Assignment.

    Replaces the private _ensure_role_assignment helper in views.py.
    """
    from permissions.models import Assignment, Role, Scope

    role_map = {
        "owner": "admin",
        "admin": "admin",
        "member": "member",
        "viewer": "viewer",
        "external": "viewer",
    }
    system_role_name = role_map.get(str(membership_role).lower(), "viewer")
    role = Role.objects.filter(name=system_role_name, is_system=True).first()
    if not role:
        return

    Assignment.objects.filter(
        tenant_id=org.tenant_id,
        user_id=user.pk,
    ).delete()

    scope, _ = Scope.objects.get_or_create(
        tenant_id=org.tenant_id,
        scope_type=Scope.SCOPE_TENANT,
    )
    Assignment.objects.create(
        tenant_id=org.tenant_id,
        user_id=user.pk,
        role=role,
        scope=scope,
        created_by_user_id=user.pk,
    )


def remove_member_from_org(org, membership) -> None:
    """Delete a member's assignments and membership."""
    from permissions.models import Assignment

    Assignment.objects.filter(
        tenant_id=org.tenant_id,
        user_id=membership.user_id,
    ).delete()
    membership.delete()


def get_user_memberships(user):
    """Return Memberships for a user with organization prefetched."""
    from tenancy.models import Membership

    return (
        Membership.objects.filter(user=user)
        .select_related("organization")
        .order_by("organization__name")
    )


# ---------------------------------------------------------------------------
# Facility services
# ---------------------------------------------------------------------------


def get_facilities_for_site(site_id, tenant_id):
    """Return active Facilities for a given site."""
    from tenancy.models import Facility

    return Facility.objects.filter(
        tenant_id=tenant_id, site_id=site_id, is_active=True
    ).order_by("name")


def get_all_facilities(tenant_id):
    """Return all active Facilities for a tenant."""
    from tenancy.models import Facility

    return Facility.objects.filter(
        tenant_id=tenant_id, is_active=True
    ).select_related("site").order_by("site__name", "name")


def create_facility(tenant_id, site, name: str, code: str = "", facility_type: str = "production", description: str = ""):
    """Create and return a new Facility."""
    from tenancy.models import Facility

    return Facility.objects.create(
        tenant_id=tenant_id,
        site=site,
        name=name,
        code=code,
        facility_type=facility_type,
        description=description,
    )


def update_facility(facility, **kwargs):
    """Update a Facility and return it."""
    for field, value in kwargs.items():
        setattr(facility, field, value)
    facility.save()
    return facility


def delete_facility(facility) -> None:
    """Soft-delete a Facility."""
    facility.is_active = False
    facility.save(update_fields=["is_active", "updated_at"])


# -----------------------------------------------------------------------
# AI: Facility data extraction from PDF text
# -----------------------------------------------------------------------

_FACILITY_EXTRACT_PROMPT = """Extrahiere strukturierte Standortdaten aus dem folgenden Dokumenttext.
Antworte NUR mit einem JSON-Objekt (kein Markdown, keine Erklärung) mit diesen Feldern:

{{
  "name": "Name der Anlage/des Standorts oder null",
  "code": "Kürzel z.B. H1 oder null",
  "facility_type": "production|storage|lab|office|workshop|other oder null",
  "description": "Kurzbeschreibung max. 300 Zeichen oder null",
  "address": "Vollständige Adresse oder null",
  "area_sqm": Zahl oder null,
  "notes": "Weitere relevante Infos oder null"
}}

Dokumenttext (Auszug):
{text}"""


def extract_facility_data_from_text(extracted_text: str) -> dict:
    """Use aifw (Groq fast inference) to extract structured facility fields from PDF text.

    Returns a dict with keys: name, code, facility_type, description, address, area_sqm, notes.
    Empty dict on failure (caller decides what to do).
    """
    if not extracted_text or len(extracted_text.strip()) < 50:
        return {}

    snippet = extracted_text[:3000]
    prompt = _FACILITY_EXTRACT_PROMPT.format(text=snippet)

    try:
        from aifw.service import sync_completion

        result = sync_completion(
            "facility_extraction",
            messages=[{"role": "user", "content": prompt}],
        )
        if not result.success:
            logger.warning("facility_extraction LLM failed: %s", result.error)
            return {}

        raw = result.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        return {k: v for k, v in data.items() if v is not None}

    except json.JSONDecodeError as exc:
        logger.warning("facility_extraction JSON parse error: %s", exc)
        return {}
    except Exception as exc:
        logger.exception("facility_extraction failed: %s", exc)
        return {}
