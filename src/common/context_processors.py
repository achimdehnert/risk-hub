"""Template context processors."""

from django.http import HttpRequest

from common.context import get_context


def tenant_context(request: HttpRequest) -> dict:
    """Add tenant info to template context."""
    ctx = get_context()
    return {
        "tenant_id": ctx.tenant_id,
        "tenant_slug": ctx.tenant_slug,
        "request_id": ctx.request_id,
    }
