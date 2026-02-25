"""
Context Processors
==================

Template Context für Tenant-Informationen.
"""

from apps.core.request_context import get_context


def tenant_context(request):
    """
    Fügt Tenant-Informationen zum Template Context hinzu.
    
    Verwendung in Templates:
        {{ tenant_slug }}
        {{ tenant_id }}
    """
    ctx = get_context()
    return {
        "tenant_slug": ctx.tenant_slug,
        "tenant_id": ctx.tenant_id,
        "request_id": ctx.request_id,
    }
