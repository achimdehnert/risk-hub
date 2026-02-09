"""Tenancy models — Organization, Site, Membership (ADR-003)."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Organization(models.Model):
    """Tenant organization with lifecycle management (ADR-003 §2.1)."""

    class Status(models.TextChoices):
        TRIAL = "trial", "Trial"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        DELETED = "deleted", "Deleted"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(
        unique=True, default=uuid.uuid4, editable=False,
    )
    slug = models.SlugField(max_length=63, unique=True)
    name = models.CharField(max_length=200)

    # Lifecycle
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TRIAL,
    )
    plan_code = models.CharField(max_length=50, default="free")
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_reason = models.TextField(blank=True, default="")
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Tenant-specific config (not for structured data)
    settings = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tenancy_organization"
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    status__in=["trial", "active", "suspended", "deleted"],
                ),
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


class Site(models.Model):
    """Physical site/location within an organization."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="sites",
    )
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tenancy_site"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_site_name_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    """Tenant membership — maps user to organization (ADR-003 §2.2)."""

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"
        VIEWER = "viewer", "Viewer"
        EXTERNAL = "external", "External"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.MEMBER,
    )
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

    class Meta:
        db_table = "tenancy_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "user"],
                name="membership_unique",
            ),
            models.CheckConstraint(
                check=models.Q(
                    role__in=[
                        "owner", "admin", "member",
                        "viewer", "external",
                    ],
                ),
                name="membership_role_chk",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "role"],
                name="idx_membership_tenant_role",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} \u2192 {self.tenant_id} ({self.role})"
