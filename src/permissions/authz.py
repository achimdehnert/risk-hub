from __future__ import annotations

from dataclasses import dataclass

from bfagent_core import get_context
from django.db.models import Q
from django.utils import timezone

from permissions.models import Assignment, Scope


@dataclass(frozen=True)
class PermissionDenied(Exception):
    permission_code: str

    def __str__(self) -> str:
        return f"Missing permission: {self.permission_code}"


def require_permission(permission_code: str) -> None:
    ctx = get_context()
    if ctx.tenant_id is None:
        raise PermissionDenied(permission_code=permission_code)
    if ctx.user_id is None:
        raise PermissionDenied(permission_code=permission_code)

    now = timezone.now()

    has_permission = (
        Assignment.objects.filter(
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id,
            role__permissions__code=permission_code,
            scope__scope_type=Scope.SCOPE_TENANT,
        )
        .filter(Q(valid_from__isnull=True) | Q(valid_from__lte=now))
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=now))
        .exists()
    )

    if not has_permission:
        raise PermissionDenied(permission_code=permission_code)
