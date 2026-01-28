"""Permission models (RBAC with Scope)."""

import uuid
from django.db import models


class Permission(models.Model):
    """Permission definition."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "permissions_permission"

    def __str__(self) -> str:
        return self.code


class Role(models.Model):
    """Role with permissions (per tenant)."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=120)
    is_system = models.BooleanField(default=False)
    permissions = models.ManyToManyField(Permission, through="RolePermission", related_name="roles")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "permissions_role"
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "name"], name="uq_permissions_role_name_per_tenant"),
        ]

    def __str__(self) -> str:
        return self.name


class RolePermission(models.Model):
    """Role-Permission mapping."""
    
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "permissions_role_permission"
        constraints = [
            models.UniqueConstraint(fields=["role", "permission"], name="uq_role_permission"),
        ]


class Scope(models.Model):
    """Scope for permission assignment (TENANT/SITE/ASSET)."""
    
    SCOPE_TENANT = "TENANT"
    SCOPE_SITE = "SITE"
    SCOPE_ASSET = "ASSET"
    SCOPE_CHOICES = [(SCOPE_TENANT, "Tenant"), (SCOPE_SITE, "Site"), (SCOPE_ASSET, "Asset")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    scope_type = models.CharField(max_length=12, choices=SCOPE_CHOICES)
    site_id = models.UUIDField(null=True, blank=True, db_index=True)
    asset_id = models.UUIDField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "permissions_scope"
        constraints = [
            models.CheckConstraint(
                check=models.Q(scope_type__in=["TENANT", "SITE", "ASSET"]),
                name="ck_scope_type_valid",
            ),
        ]

    def __str__(self) -> str:
        if self.scope_type == self.SCOPE_TENANT:
            return f"TENANT:{self.tenant_id}"
        if self.scope_type == self.SCOPE_SITE:
            return f"SITE:{self.site_id}"
        return f"ASSET:{self.asset_id}"


class Assignment(models.Model):
    """User-Role-Scope assignment."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    scope = models.ForeignKey(Scope, on_delete=models.CASCADE)
    created_by_user_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "permissions_assignment"
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "user_id", "role", "scope"], name="uq_assignment"),
        ]
