"""Common tenant utilities."""

from django.http import HttpRequest, HttpResponse, HttpResponseForbidden


def require_tenant(request: HttpRequest) -> HttpResponse | None:
    """Return 403 if request has no tenant_id, else None."""
    tenant_id = getattr(request, "tenant_id", None)
    if tenant_id is None:
        return HttpResponseForbidden("Missing tenant")
    return None


def resolve_tenant_id(request: HttpRequest):
    """Resolve tenant_id from request context or user membership (dev fallback)."""
    from common.context import get_context

    tenant_id = get_context().tenant_id
    if not tenant_id and getattr(request, "user", None) and request.user.is_authenticated:
        try:
            from django_tenancy.models import Membership

            m = (
                Membership.objects.filter(user=request.user)
                .select_related("organization")
                .order_by("created_at")
                .first()
            )
            if m and m.organization.is_active:
                tenant_id = m.organization.tenant_id
        except Exception:
            pass
    return tenant_id


def get_active_modules(request: HttpRequest) -> set[str]:
    """Return set of active module codes for the current tenant."""
    tenant_id = resolve_tenant_id(request)
    if not tenant_id:
        return set()
    try:
        from django_tenancy.module_models import ModuleSubscription

        return set(
            ModuleSubscription.objects.filter(
                tenant_id=tenant_id,
                status__in=["trial", "active"],
            ).values_list("module", flat=True)
        )
    except Exception:
        return set()
