"""Authorization service — ADR-003 §5.2 with override support."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from django.db.models import Q
from django.utils import timezone

from common.context import get_context
from permissions.models import (
    Assignment,
    PermissionOverride,
    Scope,
)


@dataclass(frozen=True)
class PermissionDenied(Exception):
    permission_code: str

    def __str__(self) -> str:
        return f"Missing permission: {self.permission_code}"


def has_permission(
    user_id: UUID,
    tenant_id: UUID,
    permission_code: str,
    scope_type: str = Scope.SCOPE_TENANT,
) -> bool:
    """Check if user has permission in tenant (ADR-003 §5.2).

    Order of evaluation:
    1. Explicit deny override \u2192 deny
    2. Explicit grant override \u2192 allow
    3. Role-based permission \u2192 allow/deny
    """
    from tenancy.models import Membership

    membership = Membership.objects.filter(
        tenant_id=tenant_id,
        user_id=user_id,
    ).first()

    if not membership:
        return False

    # 1. Check explicit deny
    deny = PermissionOverride.objects.filter(
        membership=membership,
        permission__code=permission_code,
        allowed=False,
    ).filter(
        Q(expires_at__isnull=True)
        | Q(expires_at__gte=timezone.now()),
    ).exists()
    if deny:
        return False

    # 2. Check explicit grant
    grant = PermissionOverride.objects.filter(
        membership=membership,
        permission__code=permission_code,
        allowed=True,
    ).filter(
        Q(expires_at__isnull=True)
        | Q(expires_at__gte=timezone.now()),
    ).exists()
    if grant:
        return True

    # 3. Check role-based
    now = timezone.now()
    return (
        Assignment.objects.filter(
            tenant_id=tenant_id,
            user_id=user_id,
            role__permissions__code=permission_code,
            scope__scope_type=scope_type,
        )
        .filter(Q(valid_from__isnull=True) | Q(valid_from__lte=now))
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=now))
        .exists()
    )


def require_permission(permission_code: str) -> None:
    """Raise PermissionDenied if current user lacks permission.

    When the permission system is not yet bootstrapped (zero
    Permission rows), all checks pass to avoid blocking the
    application during initial setup.
    """
    from permissions.models import Permission

    if Permission.objects.count() == 0:
        return

    ctx = get_context()
    if ctx.tenant_id is None or ctx.user_id is None:
        raise PermissionDenied(permission_code=permission_code)

    if not has_permission(ctx.user_id, ctx.tenant_id, permission_code):
        raise PermissionDenied(permission_code=permission_code)
