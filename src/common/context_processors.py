"""Template context processors."""

from django.http import HttpRequest

from common.context import get_context


def tenant_context(request: HttpRequest) -> dict:
    """Add tenant info + active module codes to template context."""
    ctx = get_context()
    tenant_id = ctx.tenant_id

    # Dev fallback: no subdomain → resolve tenant from user's membership
    if not tenant_id and getattr(request, "user", None) and request.user.is_authenticated:
        try:
            from django_tenancy.models import Membership
            m = (
                Membership.objects
                .filter(user=request.user)
                .select_related("organization")
                .order_by("created_at")
                .first()
            )
            if m and m.organization.is_active:
                tenant_id = m.organization.tenant_id
        except Exception:
            pass

    active_modules: set[str] = set()
    if tenant_id:
        try:
            from django_tenancy.module_models import ModuleSubscription
            active_modules = set(
                ModuleSubscription.objects.filter(
                    tenant_id=tenant_id,
                    status__in=["trial", "active"],
                ).values_list("module", flat=True)
            )
        except Exception:
            pass

    return {
        "tenant_id": tenant_id or ctx.tenant_id,
        "tenant_slug": ctx.tenant_slug,
        "request_id": ctx.request_id,
        "active_modules": active_modules,
    }
