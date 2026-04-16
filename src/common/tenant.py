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
            from tenancy.models import Membership

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
    """Return set of module codes the current user may access.

    Intersects tenant-level ModuleSubscription (active/trial) with
    user-level ModuleMembership.  Staff users see all subscribed modules.
    """
    tenant_id = resolve_tenant_id(request)
    if not tenant_id:
        return set()
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    try:
        from django_tenancy.module_models import ModuleMembership, ModuleSubscription

        subscribed = set(
            ModuleSubscription.objects.filter(
                tenant_id=tenant_id,
                status__in=["trial", "active"],
            ).values_list("module", flat=True)
        )
        if user.is_staff:
            return subscribed
        user_modules = set(
            ModuleMembership.objects.filter(
                tenant_id=tenant_id,
                user=user,
            ).values_list("module", flat=True)
        )
        return subscribed & user_modules
    except Exception:
        return set()
