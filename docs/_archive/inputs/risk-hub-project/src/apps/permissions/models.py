"""
Permissions Models
==================

RBAC mit Scope-Mechanismus:
- Permission: Einzelne Berechtigung (z.B. risk.assessment.read)
- Role: Sammlung von Permissions
- Scope: Geltungsbereich (Tenant/Site/Asset)
- Assignment: User -> Role -> Scope
"""

import uuid
from enum import Enum

from django.db import models

from apps.core.models import TenantModel


class ScopeType(str, Enum):
    """Scope-Typen für Berechtigungen."""

    TENANT = "TENANT"
    SITE = "SITE"
    ASSET = "ASSET"


class Permission(models.Model):
    """
    Einzelne Berechtigung.
    
    Format: {module}.{resource}.{action}
    Beispiel: risk.assessment.read
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    module = models.CharField(max_length=50, db_index=True)

    class Meta:
        db_table = "permissions_permission"
        ordering = ["module", "code"]

    def __str__(self):
        return self.code

    @classmethod
    def get_or_create_permission(cls, code: str, name: str = "", description: str = ""):
        """Permission erstellen oder abrufen."""
        module = code.split(".")[0] if "." in code else "general"
        permission, _ = cls.objects.get_or_create(
            code=code,
            defaults={
                "name": name or code,
                "description": description,
                "module": module,
            },
        )
        return permission


class Role(TenantModel):
    """
    Rolle mit zugewiesenen Permissions.
    
    Rollen sind Tenant-spezifisch, aber können System-Defaults haben.
    """

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False, help_text="System-Rolle (nicht löschbar)")
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)

    class Meta:
        db_table = "permissions_role"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"], name="uq_role_name_per_tenant"
            ),
        ]

    def __str__(self):
        return self.name


class Scope(TenantModel):
    """
    Geltungsbereich für Berechtigungen.
    
    Hierarchie:
    - TENANT: Gesamter Mandant
    - SITE: Bestimmter Standort
    - ASSET: Bestimmte Anlage/Asset
    """

    scope_type = models.CharField(
        max_length=20,
        choices=[(t.value, t.name) for t in ScopeType],
    )

    # Optional: Referenz auf Site oder Asset
    site = models.ForeignKey(
        "tenancy.Site",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="permission_scopes",
    )
    # asset = models.ForeignKey("assets.Asset", ...)  # Später

    class Meta:
        db_table = "permissions_scope"
        constraints = [
            # Wenn SITE, muss site_id gesetzt sein
            models.CheckConstraint(
                check=(
                    models.Q(scope_type="TENANT", site__isnull=True)
                    | models.Q(scope_type="SITE", site__isnull=False)
                    | models.Q(scope_type="ASSET")
                ),
                name="ck_scope_type_consistency",
            ),
        ]

    def __str__(self):
        if self.scope_type == ScopeType.TENANT.value:
            return f"Tenant Scope"
        elif self.scope_type == ScopeType.SITE.value:
            return f"Site Scope: {self.site}"
        return f"Scope: {self.scope_type}"


class Assignment(TenantModel):
    """
    Zuweisung: User -> Role -> Scope.
    
    Beispiel: Max Mustermann ist "Site Safety Officer" für "Standort Berlin"
    """

    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="permission_assignments",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    scope = models.ForeignKey(
        Scope,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    # Audit
    created_by = models.ForeignKey(
        "identity.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_assignments",
    )

    class Meta:
        db_table = "permissions_assignment"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "user", "role", "scope"],
                name="uq_assignment_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "user"]),
        ]

    def __str__(self):
        return f"{self.user} -> {self.role} ({self.scope})"
