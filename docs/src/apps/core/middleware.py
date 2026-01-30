"""
Middleware
==========

Request-Processing Middleware für:
- Request Context (request_id, user_id)
- Subdomain Tenant Resolution
- Postgres RLS Session Variables
"""

import uuid

from django.conf import settings
from django.db import connection
from django.http import HttpRequest, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

from apps.core.request_context import (
    clear_context,
    set_request_id,
    set_tenant,
    set_user_id,
)


def _parse_subdomain(host: str) -> str | None:
    """
    Subdomain aus Host extrahieren.
    
    demo.localhost → "demo"
    demo.risk-hub.de → "demo"
    localhost → None
    """
    host = host.split(":")[0].lower()
    base = settings.TENANT_BASE_DOMAIN.lower()

    # Exact match (kein Subdomain)
    if host == base:
        return None

    # Subdomain vorhanden
    if host.endswith("." + base):
        return host[: -(len(base) + 1)]

    return None


def _set_db_tenant(tenant_id: uuid.UUID | None) -> None:
    """
    Postgres Session Variable für RLS setzen.
    
    Policy: tenant_id = current_setting('app.current_tenant')::uuid
    """
    if not settings.DATABASE_RLS_ENABLED:
        return

    value = "" if tenant_id is None else str(tenant_id)
    with connection.cursor() as cur:
        cur.execute("SELECT set_config('app.current_tenant', %s, true)", [value])


class RequestContextMiddleware(MiddlewareMixin):
    """
    Request Context initialisieren.
    
    - Generiert request_id (oder übernimmt aus Header)
    - Setzt user_id wenn authenticated
    """

    def process_request(self, request: HttpRequest) -> None:
        # Request ID (für Tracing/Logging)
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)

        # User ID
        if hasattr(request, "user") and request.user.is_authenticated:
            set_user_id(request.user.id)
        else:
            set_user_id(None)

        # Request ID auch auf Request setzen für Templates
        request.request_id = request_id

    def process_response(self, request: HttpRequest, response):
        # Request ID in Response Header
        if hasattr(request, "request_id"):
            response["X-Request-ID"] = request.request_id

        # Context clearen
        clear_context()
        return response


class SubdomainTenantMiddleware(MiddlewareMixin):
    """
    Tenant aus Subdomain auflösen.
    
    demo.risk-hub.de → Organization mit slug="demo"
    """

    def process_request(self, request: HttpRequest):
        from apps.tenancy.models import Organization

        subdomain = _parse_subdomain(request.get_host())

        # Kein Subdomain
        if not subdomain:
            # Admin ohne Tenant erlauben (nur Dev)
            if settings.TENANT_ALLOW_LOCALHOST and request.path.startswith("/admin/"):
                set_tenant(None, None)
                _set_db_tenant(None)
                return None

            # Health Check ohne Tenant
            if request.path == "/health/":
                set_tenant(None, None)
                return None

            return HttpResponseForbidden("Missing tenant subdomain")

        # Tenant suchen
        org = Organization.objects.filter(slug=subdomain).first()
        if not org:
            return HttpResponseForbidden(f"Unknown tenant: {subdomain}")

        # Context setzen
        set_tenant(org.tenant_id, org.slug)
        _set_db_tenant(org.tenant_id)

        # Für Templates
        request.tenant = org
        request.tenant_id = org.tenant_id
        request.tenant_slug = org.slug

        return None
