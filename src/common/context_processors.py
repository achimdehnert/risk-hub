"""Template context processors."""

from django.http import HttpRequest

from common.context import get_context
from common.tenant import get_active_modules, resolve_tenant_id


def tenant_context(request: HttpRequest) -> dict:
    """Add tenant info + active module codes to template context."""
    ctx = get_context()
    tenant_id = resolve_tenant_id(request)

    current_org = getattr(request, "tenant", None)
    user_memberships = []
    if request.user.is_authenticated:
        try:
            from tenancy.services import get_user_memberships
            user_memberships = [
                m for m in get_user_memberships(request.user)
                if m.organization.is_active
            ]
        except Exception:
            pass

    return {
        "tenant_id": tenant_id or ctx.tenant_id,
        "tenant_slug": ctx.tenant_slug,
        "request_id": ctx.request_id,
        "active_modules": get_active_modules(request),
        "stripe_sub": None,
        "current_org": current_org,
        "user_memberships": user_memberships,
    }
