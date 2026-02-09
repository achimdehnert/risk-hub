"""Common tenant utilities."""

from django.http import HttpRequest, HttpResponse, HttpResponseForbidden


def require_tenant(request: HttpRequest) -> HttpResponse | None:
    """Return 403 if request has no tenant_id, else None."""
    tenant_id = getattr(request, "tenant_id", None)
    if tenant_id is None:
        return HttpResponseForbidden("Missing tenant")
    return None
