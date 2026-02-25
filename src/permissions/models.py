"""Permission models — RBAC with Scope & Overrides (ADR-003)."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Permission(models.Model):
    """Permission definition (ADR-003 §2.3)."""

    class Action(models.TextChoices):
        VIEW = "view", "View"
        CREATE = "create", "Create"
        EDIT = "edit", "Edit"
        DELETE = "delete", "Delete"
        MANAGE = "manage", "Manage"
        EXPORT = "export", "Export"
        APPROVE = "approve", "Approve"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    code = models.CharField(max_length=100, unique=True)
    module = models.CharField(max_length=50, db_index=True)
    resource = models.CharField(max_length=50)
    action = models.CharField(
        max_length=20, choices=Action.choices, default=Action.VIEW,
    )
    description = models.TextField(blank=True, default="")
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "permissions_permission"
        indexes = [
            models.Index(
                fields=["module", "resource"],
                name="idx_perm_module_resource",
            ),
        ]

    def __str__(self) -> str:
        return self.code


class Role(models.Model):
    """Role with permissions, per tenant or system (ADR-003 §2.4)."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    is_system = models.BooleanField(default=False)
    permissions = models.ManyToManyField(
        Permission, through="RolePermission", related_name="roles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "permissions_role"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_permissions_role_name_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class RolePermission(models.Model):
    """Role \u2192 Permission mapping."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "permissions_role_permission"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="uq_role_permission",
            ),
        ]


class Scope(models.Model):
    """Scope for permission assignment (ADR-003 §2.5)."""

    SCOPE_TENANT = "TENANT"
    SCOPE_SITE = "SITE"
    SCOPE_ASSET = "ASSET"
    SCOPE_CHOICES = [
        (SCOPE_TENANT, "Tenant"),
        (SCOPE_SITE, "Site"),
        (SCOPE_ASSET, "Asset"),
    ]

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    scope_type = models.CharField(max_length=12, choices=SCOPE_CHOICES)
    site_id = models.UUIDField(null=True, blank=True, db_index=True)
    asset_id = models.UUIDField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "permissions_scope"
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    scope_type__in=["TENANT", "SITE", "ASSET"],
                ),
                name="ck_scope_type_valid",
            ),
            models.CheckConstraint(
                check=(
                    ~models.Q(scope_type="SITE")
                    | models.Q(site_id__isnull=False)
                ),
                name="scope_site_chk",
            ),
            models.CheckConstraint(
                check=(
                    ~models.Q(scope_type="ASSET")
                    | models.Q(asset_id__isnull=False)
                ),
                name="scope_asset_chk",
            ),
        ]

    def __str__(self) -> str:
        if self.scope_type == self.SCOPE_TENANT:
            return f"TENANT:{self.tenant_id}"
        if self.scope_type == self.SCOPE_SITE:
            return f"SITE:{self.site_id}"
        return f"ASSET:{self.asset_id}"


class Assignment(models.Model):
    """User \u2192 Role \u2192 Scope assignment (ADR-003 §2.5)."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="assignments",
    )
    scope = models.ForeignKey(Scope, on_delete=models.CASCADE)
    created_by_user_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "permissions_assignment"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "user_id", "role", "scope"],
                name="uq_assignment",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "user_id"],
                name="idx_assignment_user",
            ),
        ]


class PermissionOverride(models.Model):
    """Explicit grant/deny override per membership (ADR-003 §2.4)."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    membership = models.ForeignKey(
        "django_tenancy.Membership",
        on_delete=models.CASCADE,
        related_name="permission_overrides",
    )
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE,
    )
    allowed = models.BooleanField(
        help_text="True = grant, False = deny",
    )
    reason = models.TextField(blank=True, default="")
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "permissions_override"
        constraints = [
            models.UniqueConstraint(
                fields=["membership", "permission"],
                name="override_unique",
            ),
        ]
