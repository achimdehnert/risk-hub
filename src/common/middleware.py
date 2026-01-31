"""Middleware for Risk-Hub."""

import uuid

from common.context import set_db_tenant, set_request_id, set_tenant, set_user_id
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin


def _parse_subdomain(host: str, base_domain: str) -> str | None:
    """Extract subdomain from host."""
    host = host.split(":")[0].lower()
    base = base_domain.lower()

    if host == base:
        return None

    if host.endswith("." + base):
        return host[: -(len(base) + 1)]

    return None


class RequestContextMiddleware(MiddlewareMixin):
    """Set up request context (request_id, user_id)."""

    def process_request(self, request: HttpRequest) -> None:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        set_request_id(request_id)

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            set_user_id(user.id if hasattr(user, "id") else None)
        else:
            set_user_id(None)


class SubdomainTenantMiddleware(MiddlewareMixin):
    """Subdomain-based tenant resolution."""

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        base_domains = list(getattr(settings, "TENANT_BASE_DOMAINS", []))
        if not base_domains:
            base_domains = [
                getattr(settings, "TENANT_BASE_DOMAIN", "localhost"),
            ]
        allow_localhost = getattr(settings, "TENANT_ALLOW_LOCALHOST", False)
        reserved_subdomains = set(
            getattr(settings, "TENANT_RESERVED_SUBDOMAINS", ["www"])
        )

        host = request.get_host().split(":")[0].lower()
        if host in {d.lower() for d in base_domains}:
            set_tenant(None, None)
            set_db_tenant(None)
            return None

        subdomain = None
        for base_domain in base_domains:
            subdomain = _parse_subdomain(request.get_host(), base_domain)
            if subdomain:
                break

        if subdomain and subdomain.lower() in reserved_subdomains:
            set_tenant(None, None)
            set_db_tenant(None)
            return None

        if not subdomain:
            # Check for X-Tenant-ID header (for tests and API clients)
            header_tenant = request.headers.get("X-Tenant-Id")
            if header_tenant:
                try:
                    tenant_uuid = uuid.UUID(header_tenant)
                    set_tenant(tenant_uuid, None)
                    set_db_tenant(tenant_uuid)
                    request.tenant_id = tenant_uuid
                    return None
                except (ValueError, TypeError):
                    pass
            
            if request.path.startswith("/api/"):
                set_tenant(None, None)
                set_db_tenant(None)
                return None
            if request.path.startswith("/ex/"):
                # Allow explosionsschutz paths without tenant for tests
                set_tenant(None, None)
                set_db_tenant(None)
                return None
            if allow_localhost and request.path.startswith("/admin/"):
                set_tenant(None, None)
                set_db_tenant(None)
                return None
            return HttpResponseForbidden("Missing tenant subdomain")

        # Look up tenant (with error handling for missing tables during
        # migrations)
        try:
            from tenancy.models import Organization
            org = Organization.objects.filter(slug=subdomain).first()
        except Exception:
            # Tables don't exist yet (during migrations)
            set_tenant(None, subdomain)
            set_db_tenant(None)
            return None

        if not org:
            return HttpResponseForbidden(f"Unknown tenant: {subdomain}")

        set_tenant(org.tenant_id, subdomain)
        set_db_tenant(org.tenant_id)

        request.tenant = org
        request.tenant_id = org.tenant_id
        request.tenant_slug = subdomain

        return None
