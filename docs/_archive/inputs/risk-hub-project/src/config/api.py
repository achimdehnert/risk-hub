"""
risk-hub API Configuration (Django Ninja)
==========================================

Zentrale API für Hub-Integration und externe Clients.
"""

from ninja import NinjaAPI
from ninja.security import HttpBearer

from apps.core.request_context import get_context


class TenantAuth(HttpBearer):
    """API Key Authentication mit Tenant-Kontext."""

    def authenticate(self, request, token):
        # TODO: Implement API Key validation
        # Für jetzt: Tenant aus Request Context
        ctx = get_context()
        if ctx.tenant_id:
            return {"tenant_id": ctx.tenant_id}
        return None


api = NinjaAPI(
    title="risk-hub API",
    version="1.0.0",
    description="Enterprise SaaS API für Risikomanagement",
    auth=TenantAuth(),
)


# =============================================================================
# Health Endpoint (kein Auth)
# =============================================================================

@api.get("/health", auth=None, tags=["System"])
def api_health(request):
    """Health Check für Monitoring."""
    return {"status": "ok"}


# =============================================================================
# Domain Routers
# =============================================================================

# Import und registriere Domain-Router
# from apps.risk.api import router as risk_router
# from apps.documents.api import router as documents_router

# api.add_router("/risk/", risk_router, tags=["Risk"])
# api.add_router("/documents/", documents_router, tags=["Documents"])


# =============================================================================
# URL Patterns
# =============================================================================

urlpatterns = [api.urls]
