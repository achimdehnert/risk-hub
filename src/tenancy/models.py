"""Tenancy models for risk-hub.

Organization, Membership and Site are defined locally. The django_tenancy
platform package provides TenantModel, ModuleSubscription, ModuleMembership.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_tenancy.managers import TenantManager

__all__ = ["Department", "Facility", "Membership", "Organization", "Site"]


class Organization(models.Model):
    """Tenant entity. One Organization = one tenant."""

    class Status(models.TextChoices):
        TRIAL = "trial", _("Trial")
        ACTIVE = "active", _("Active")
        SUSPENDED = "suspended", _("Suspended")
        DELETED = "deleted", _("Deleted")

    tenant_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    slug = models.SlugField(max_length=63, unique=True)
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRIAL)
    plan_code = models.CharField(max_length=50, default="free")
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_reason = models.TextField(blank=True, default="")
    deleted_at = models.DateTimeField(null=True, blank=True)
    settings = models.JSONField(blank=True, default=dict)
    # ADR-118 billing fields
    is_readonly = models.BooleanField(
        default=False,
        help_text="True when subscription ended — read-only access until gdpr_delete_at",
    )
    deactivation_reason = models.TextField(
        blank=True,
        default="",
        help_text="Reason provided by billing-hub on deactivation",
    )
    gdpr_delete_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Scheduled hard-delete date (90 days after deactivation, GDPR)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "tenancy"
        db_table = "tenancy_organization"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["trial", "active", "suspended", "deleted"]),
                name="org_status_chk",
            ),
        ]
        indexes = [
            models.Index(fields=["status"], name="idx_org_status"),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def is_active(self) -> bool:
        return self.status in (self.Status.TRIAL, self.Status.ACTIVE)


class Membership(models.Model):
    """Links a User to an Organization with a role."""

    class Role(models.TextChoices):
        OWNER = "owner", _("Owner")
        ADMIN = "admin", _("Admin")
        MEMBER = "member", _("Member")
        VIEWER = "viewer", _("Viewer")
        EXTERNAL = "external", _("External")

    tenant_id = models.UUIDField(db_index=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tenancy_memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    invited_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        app_label = "tenancy"
        db_table = "tenancy_membership"
        constraints = [
            models.UniqueConstraint(fields=("tenant_id", "user"), name="membership_unique"),
            models.CheckConstraint(
                condition=models.Q(role__in=["owner", "admin", "member", "viewer", "external"]),
                name="membership_role_chk",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "role"], name="idx_membership_tenant_role"),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.organization} ({self.role})"


class Site(models.Model):
    """Physical site/location within an organization (UC-004)."""

    class SiteType(models.TextChoices):
        PLANT = "plant", _("Werk")
        WAREHOUSE = "warehouse", _("Lager")
        OFFICE = "office", _("Büro")
        LAB = "lab", _("Labor")
        OTHER = "other", _("Sonstiges")

    tenant_id = models.UUIDField(db_index=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="sites",
    )
    name = models.CharField(max_length=200)
    code = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text=_("Standortkürzel (z.B. 'A', 'FR')"),
    )
    site_type = models.CharField(
        max_length=20,
        choices=SiteType.choices,
        default=SiteType.PLANT,
        help_text=_("Standorttyp"),
    )
    address = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        app_label = "tenancy"
        db_table = "tenancy_site"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_site_name_per_tenant",
            ),
            models.UniqueConstraint(
                fields=["tenant_id", "code"],
                name="uq_site_code_per_tenant",
                condition=~models.Q(code=""),
            ),
        ]

    def __str__(self) -> str:
        if self.code:
            return f"{self.name} ({self.code})"
        return self.name


class Facility(models.Model):
    """Physical production unit within a Site (Werk, Halle, Labor)."""

    class FacilityType(models.TextChoices):
        PRODUCTION = "production", _("Produktion")
        STORAGE = "storage", _("Lager")
        LAB = "lab", _("Labor")
        OFFICE = "office", _("Büro")
        WORKSHOP = "workshop", _("Werkstatt")
        OTHER = "other", _("Sonstiges")

    tenant_id = models.UUIDField(db_index=True)
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="facilities",
    )
    name = models.CharField(max_length=200)
    code = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text=_("Kürzel (z.B. 'H1', 'R2')"),
    )
    facility_type = models.CharField(
        max_length=20,
        choices=FacilityType.choices,
        default=FacilityType.PRODUCTION,
    )
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        app_label = "tenancy"
        db_table = "tenancy_facility"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "site", "name"],
                name="uq_facility_name_per_site",
            ),
            models.UniqueConstraint(
                fields=["tenant_id", "site", "code"],
                name="uq_facility_code_per_site",
                condition=~models.Q(code=""),
            ),
        ]

    def __str__(self) -> str:
        if self.code:
            return f"{self.name} ({self.code})"
        return self.name


class Department(models.Model):
    """Department within an organization, optionally bound to a site (UC-004)."""

    tenant_id = models.UUIDField(db_index=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="departments",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="departments",
        help_text=_("Standort (leer = standortübergreifend)"),
    )
    name = models.CharField(max_length=200)
    code = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text=_("Abteilungskürzel (z.B. 'PROD', 'HT')"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        app_label = "tenancy"
        db_table = "tenancy_department"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "organization", "site", "name"],
                name="uq_department_per_org_site",
            ),
        ]

    def __str__(self) -> str:
        site_label = f" @ {self.site.name}" if self.site else ""
        return f"{self.name}{site_label}"
