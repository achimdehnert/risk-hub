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

__all__ = ["Membership", "Organization", "Site"]


class Organization(models.Model):
    """Tenant entity. One Organization = one tenant."""

    class Status(models.TextChoices):
        TRIAL = "trial", _("Trial")
        ACTIVE = "active", _("Active")
        SUSPENDED = "suspended", _("Suspended")
        DELETED = "deleted", _("Deleted")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    """Physical site/location within an organization."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="sites",
    )
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        app_label = "tenancy"
        db_table = "tenancy_site"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_site_name_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return self.name
