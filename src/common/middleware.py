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


def _sync_platform_context(
    tenant_id=None, slug=None, request_id=None, user_id=None,
):
    """Sync state with platform_context (ADR-028).

    risk-hub keeps its own common.context as primary source
    (different SQL variable: app.tenant_id vs app.current_tenant).
    This sync ensures platform_context consumers also see the
    current request context.
    """
    try:
        from platform_context import context as pc

        if request_id:
            pc.set_request_id(request_id)
        if user_id is not None:
            pc.set_user_id(user_id)
        pc.set_tenant(tenant_id, slug)
    except ImportError:
        pass


class RequestContextMiddleware(MiddlewareMixin):
    """Set up request context (request_id, user_id)."""

    def process_request(self, request: HttpRequest) -> None:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        set_request_id(request_id)

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            uid = user.id if hasattr(user, "id") else None
            set_user_id(uid)
            _sync_platform_context(request_id=request_id, user_id=uid)
        else:
            set_user_id(None)
            _sync_platform_context(request_id=request_id, user_id=None)


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
            _sync_platform_context()
            return None

        subdomain = None
        for base_domain in base_domains:
            subdomain = _parse_subdomain(request.get_host(), base_domain)
            if subdomain:
                break

        if subdomain and subdomain.lower() in reserved_subdomains:
            set_tenant(None, None)
            set_db_tenant(None)
            _sync_platform_context()
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
                    _sync_platform_context(tenant_id=tenant_uuid)
                    return None
                except (ValueError, TypeError):
                    pass

            # Allow only truly public paths without tenant
            public_prefixes = [
                "/static/",
                "/livez/",
                "/healthz/",
                "/health/",
                "/favicon.ico",
                "/__debug__/",
                "/api/v1/",
            ]
            if any(
                request.path.startswith(p)
                for p in public_prefixes
            ):
                set_tenant(None, None)
                set_db_tenant(None)
                _sync_platform_context()
                return None
            if request.path == "/":
                set_tenant(None, None)
                set_db_tenant(None)
                _sync_platform_context()
                return None
            if allow_localhost and (
                request.path.startswith("/admin/")
                or request.path.startswith("/api/schema")
            ):
                set_tenant(None, None)
                set_db_tenant(None)
                _sync_platform_context()
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
            _sync_platform_context(slug=subdomain)
            return None

        if not org:
            return HttpResponseForbidden(f"Unknown tenant: {subdomain}")

        set_tenant(org.tenant_id, subdomain)
        set_db_tenant(org.tenant_id)

        request.tenant = org
        request.tenant_id = org.tenant_id
        request.tenant_slug = subdomain

        _sync_platform_context(tenant_id=org.tenant_id, slug=subdomain)

        return None
