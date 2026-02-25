"""
Permissions Service
===================

Authorization Logic für RBAC + Scope.

Verwendung:
    from apps.permissions.services import authorize, PermissionDenied
    
    # Einzelnes Objekt prüfen
    authorize(user, "risk.assessment.read", assessment)
    
    # Liste filtern
    queryset = filter_by_permission(user, "risk.assessment.read", Assessment.objects.all())
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import UUID

from django.db.models import QuerySet

from apps.core.request_context import get_context, require_tenant
from apps.permissions.models import Assignment, Permission, Scope, ScopeType


class PermissionDenied(Exception):
    """Zugriff verweigert."""

    def __init__(self, permission: str, message: str = ""):
        self.permission = permission
        self.message = message or f"Permission denied: {permission}"
        super().__init__(self.message)


@dataclass
class AuthorizationResult:
    """Ergebnis einer Autorisierungsprüfung."""

    allowed: bool
    permission: str
    scopes: list[Scope]
    reason: str = ""


def get_user_permissions(user, tenant_id: UUID | None = None) -> dict[str, list[Scope]]:
    """
    Alle Permissions eines Users im Tenant abrufen.
    
    Returns:
        Dict[permission_code, List[Scope]]
    """
    if tenant_id is None:
        tenant_id = require_tenant()

    assignments = (
        Assignment.objects.filter(tenant_id=tenant_id, user=user)
        .select_related("role", "scope", "scope__site")
        .prefetch_related("role__permissions")
    )

    result: dict[str, list[Scope]] = {}

    for assignment in assignments:
        for permission in assignment.role.permissions.all():
            if permission.code not in result:
                result[permission.code] = []
            result[permission.code].append(assignment.scope)

    return result


def check_permission(
    user,
    permission_code: str,
    obj: Any = None,
    tenant_id: UUID | None = None,
) -> AuthorizationResult:
    """
    Prüft ob User Permission für Objekt hat.
    
    Args:
        user: User-Objekt
        permission_code: Permission Code (z.B. "risk.assessment.read")
        obj: Optional - Objekt das geprüft wird
        tenant_id: Optional - Tenant ID (sonst aus Context)
    
    Returns:
        AuthorizationResult
    """
    if tenant_id is None:
        tenant_id = require_tenant()

    # Permissions des Users laden
    user_permissions = get_user_permissions(user, tenant_id)

    # Permission nicht vorhanden
    if permission_code not in user_permissions:
        return AuthorizationResult(
            allowed=False,
            permission=permission_code,
            scopes=[],
            reason="User does not have this permission",
        )

    scopes = user_permissions[permission_code]

    # Kein Objekt -> Permission reicht
    if obj is None:
        return AuthorizationResult(
            allowed=True,
            permission=permission_code,
            scopes=scopes,
        )

    # Objekt prüfen gegen Scopes
    for scope in scopes:
        if _scope_matches_object(scope, obj):
            return AuthorizationResult(
                allowed=True,
                permission=permission_code,
                scopes=[scope],
            )

    return AuthorizationResult(
        allowed=False,
        permission=permission_code,
        scopes=scopes,
        reason="No scope matches the object",
    )


def _scope_matches_object(scope: Scope, obj: Any) -> bool:
    """Prüft ob Scope auf Objekt zutrifft."""
    # Tenant Scope -> alles erlaubt
    if scope.scope_type == ScopeType.TENANT.value:
        return True

    # Site Scope -> Objekt muss zur Site gehören
    if scope.scope_type == ScopeType.SITE.value:
        obj_site_id = getattr(obj, "site_id", None)
        if obj_site_id and scope.site_id:
            return obj_site_id == scope.site_id

    # Asset Scope -> Objekt muss zum Asset gehören
    if scope.scope_type == ScopeType.ASSET.value:
        obj_asset_id = getattr(obj, "asset_id", None)
        # TODO: Implement asset scope check
        pass

    return False


def authorize(
    user,
    permission_code: str,
    obj: Any = None,
    tenant_id: UUID | None = None,
) -> None:
    """
    Autorisierung prüfen - wirft Exception wenn nicht erlaubt.
    
    Verwendung:
        authorize(request.user, "risk.assessment.write", assessment)
    """
    result = check_permission(user, permission_code, obj, tenant_id)
    if not result.allowed:
        raise PermissionDenied(permission_code, result.reason)


def has_permission(
    user,
    permission_code: str,
    obj: Any = None,
    tenant_id: UUID | None = None,
) -> bool:
    """Prüft Permission ohne Exception."""
    result = check_permission(user, permission_code, obj, tenant_id)
    return result.allowed


def filter_by_permission(
    user,
    permission_code: str,
    queryset: QuerySet,
    tenant_id: UUID | None = None,
) -> QuerySet:
    """
    QuerySet auf erlaubte Objekte filtern.
    
    Verwendung:
        assessments = filter_by_permission(
            user, "risk.assessment.read", 
            Assessment.objects.all()
        )
    """
    if tenant_id is None:
        tenant_id = require_tenant()

    # Permissions laden
    user_permissions = get_user_permissions(user, tenant_id)

    if permission_code not in user_permissions:
        return queryset.none()

    scopes = user_permissions[permission_code]

    # Tenant Scope -> alles erlaubt
    if any(s.scope_type == ScopeType.TENANT.value for s in scopes):
        return queryset.filter(tenant_id=tenant_id)

    # Site Scopes sammeln
    site_ids = [s.site_id for s in scopes if s.scope_type == ScopeType.SITE.value and s.site_id]

    # Asset Scopes sammeln
    # asset_ids = [s.asset_id for s in scopes if s.scope_type == ScopeType.ASSET.value]

    # Filter bauen
    from django.db.models import Q

    filters = Q(pk__in=[])  # Startet mit leerem Filter

    if site_ids:
        filters |= Q(site_id__in=site_ids)

    # if asset_ids:
    #     filters |= Q(asset_id__in=asset_ids)

    return queryset.filter(tenant_id=tenant_id).filter(filters)


# =============================================================================
# Default Permissions & Roles (Setup)
# =============================================================================

DEFAULT_PERMISSIONS = [
    # Risk
    ("risk.assessment.read", "Gefährdungsbeurteilung lesen"),
    ("risk.assessment.write", "Gefährdungsbeurteilung bearbeiten"),
    ("risk.assessment.approve", "Gefährdungsbeurteilung freigeben"),
    ("risk.assessment.delete", "Gefährdungsbeurteilung löschen"),
    # Actions
    ("actions.action.read", "Maßnahme lesen"),
    ("actions.action.write", "Maßnahme bearbeiten"),
    ("actions.action.close", "Maßnahme abschließen"),
    # Documents
    ("documents.document.read", "Dokument lesen"),
    ("documents.document.write", "Dokument hochladen"),
    ("documents.document.approve", "Dokument freigeben"),
    ("documents.document.delete", "Dokument löschen"),
    # Reports
    ("reports.export.read", "Export lesen"),
    ("reports.export.create", "Export erstellen"),
    # Admin
    ("admin.users.read", "Benutzer anzeigen"),
    ("admin.users.manage", "Benutzer verwalten"),
    ("admin.roles.manage", "Rollen verwalten"),
    ("admin.sites.manage", "Standorte verwalten"),
]

DEFAULT_ROLES = {
    "Tenant Admin": [p[0] for p in DEFAULT_PERMISSIONS],
    "EHS Manager": [
        "risk.assessment.read",
        "risk.assessment.write",
        "risk.assessment.approve",
        "actions.action.read",
        "actions.action.write",
        "actions.action.close",
        "documents.document.read",
        "documents.document.write",
        "documents.document.approve",
        "reports.export.read",
        "reports.export.create",
    ],
    "Site Safety Officer": [
        "risk.assessment.read",
        "risk.assessment.write",
        "actions.action.read",
        "actions.action.write",
        "actions.action.close",
        "documents.document.read",
        "documents.document.write",
        "reports.export.read",
        "reports.export.create",
    ],
    "Auditor": [
        "risk.assessment.read",
        "actions.action.read",
        "documents.document.read",
        "reports.export.read",
        "reports.export.create",
    ],
    "Worker": [
        "risk.assessment.read",
        "actions.action.read",
        "actions.action.write",
        "documents.document.read",
    ],
}


def setup_default_permissions() -> None:
    """Default Permissions erstellen."""
    for code, name in DEFAULT_PERMISSIONS:
        Permission.get_or_create_permission(code, name)


def setup_default_roles(tenant_id: UUID) -> None:
    """Default Roles für Tenant erstellen."""
    from apps.permissions.models import Role

    setup_default_permissions()

    for role_name, permission_codes in DEFAULT_ROLES.items():
        role, created = Role.objects.get_or_create(
            tenant_id=tenant_id,
            name=role_name,
            defaults={"is_system": True},
        )

        if created:
            permissions = Permission.objects.filter(code__in=permission_codes)
            role.permissions.set(permissions)
