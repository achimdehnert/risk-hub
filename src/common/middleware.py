"""Middleware for Risk-Hub."""

import uuid

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from common.context import (
    set_db_tenant,
    set_request_id,
    set_tenant,
    set_user_id,
)


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
    tenant_id=None,
    slug=None,
    request_id=None,
    user_id=None,
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
            _sync_platform_context(
                request_id=request_id,
                user_id=uid,
            )
        else:
            set_user_id(None)
            _sync_platform_context(
                request_id=request_id,
                user_id=None,
            )


class SubdomainTenantMiddleware(MiddlewareMixin):
    """Subdomain-based tenant resolution."""

    def process_request(
        self,
        request: HttpRequest,
    ) -> HttpResponse | None:
        base_domains = list(
            getattr(settings, "TENANT_BASE_DOMAINS", []),
        )
        if not base_domains:
            base_domains = [
                getattr(
                    settings,
                    "TENANT_BASE_DOMAIN",
                    "localhost",
                ),
            ]
        allow_localhost = getattr(
            settings,
            "TENANT_ALLOW_LOCALHOST",
            False,
        )
        reserved_subdomains = set(
            getattr(
                settings,
                "TENANT_RESERVED_SUBDOMAINS",
                ["www"],
            )
        )

        host = request.get_host().split(":")[0].lower()
        if host in {d.lower() for d in base_domains}:
            # Check for X-Tenant-ID header first (API clients / tests)
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
            # Try to resolve tenant from authenticated user before giving up
            user = getattr(request, "user", None)
            if user and user.is_authenticated:
                user_tenant_id = getattr(user, "tenant_id", None)
                if user_tenant_id:
                    try:
                        from tenancy.models import Organization

                        org = Organization.objects.filter(tenant_id=user_tenant_id).first()
                        if org:
                            set_tenant(org.tenant_id, org.slug)
                            set_db_tenant(org.tenant_id)
                            request.tenant = org
                            request.tenant_id = org.tenant_id
                            request.tenant_slug = org.slug
                            _sync_platform_context(tenant_id=org.tenant_id, slug=org.slug)
                            return None
                    except Exception:
                        pass
            set_tenant(None, None)
            set_db_tenant(None)
            _sync_platform_context()
            return None

        subdomain = None
        for base_domain in base_domains:
            subdomain = _parse_subdomain(
                request.get_host(),
                base_domain,
            )
            if subdomain:
                break

        if subdomain and subdomain.lower() in reserved_subdomains:
            set_tenant(None, None)
            set_db_tenant(None)
            _sync_platform_context()
            return None

        if not subdomain:
            # Check for X-Tenant-ID header (API clients)
            header_tenant = request.headers.get("X-Tenant-Id")
            if header_tenant:
                try:
                    tenant_uuid = uuid.UUID(header_tenant)
                    set_tenant(tenant_uuid, None)
                    set_db_tenant(tenant_uuid)
                    request.tenant_id = tenant_uuid
                    _sync_platform_context(
                        tenant_id=tenant_uuid,
                    )
                    return None
                except (ValueError, TypeError):
                    pass

            # Allow truly public paths without tenant
            public_prefixes = [
                "/static/",
                "/livez/",
                "/healthz/",
                "/health/",
                "/favicon.ico",
                "/__debug__/",
                "/api/v1/",
            ]
            if any(request.path.startswith(p) for p in public_prefixes):
                set_tenant(None, None)
                set_db_tenant(None)
                _sync_platform_context()
                return None
            if request.path == "/":
                set_tenant(None, None)
                set_db_tenant(None)
                _sync_platform_context()
                return None

            # Fallback: resolve tenant from authenticated user.tenant_id
            # Must run BEFORE allow_localhost so production (schutztat.de)
            # with TENANT_ALLOW_LOCALHOST=True still gets tenant context.
            user = getattr(request, "user", None)
            if user and user.is_authenticated:
                user_tenant_id = getattr(user, "tenant_id", None)
                if user_tenant_id:
                    try:
                        from tenancy.models import Organization

                        org = Organization.objects.filter(tenant_id=user_tenant_id).first()
                        if org:
                            set_tenant(org.tenant_id, org.slug)
                            set_db_tenant(org.tenant_id)
                            request.tenant = org
                            request.tenant_id = org.tenant_id
                            request.tenant_slug = org.slug
                            _sync_platform_context(tenant_id=org.tenant_id, slug=org.slug)
                            return None
                    except Exception:
                        pass

            if allow_localhost:
                set_tenant(None, None)
                set_db_tenant(None)
                _sync_platform_context()
                return None

            # Public login / accounts paths — allow without tenant
            accounts_prefixes = ["/accounts/", "/tenants/", "/admin/"]
            if any(request.path.startswith(p) for p in accounts_prefixes):
                set_tenant(None, None)
                set_db_tenant(None)
                _sync_platform_context()
                return None

            from django.conf import settings as _s
            from django.shortcuts import redirect as _r

            login_url = getattr(_s, "LOGIN_URL", "/accounts/login/")
            return _r(f"{login_url}?next={request.path}")

        # Look up tenant
        try:
            from tenancy.models import Organization

            org = Organization.objects.filter(
                slug=subdomain,
            ).first()
        except Exception:
            set_tenant(None, subdomain)
            set_db_tenant(None)
            _sync_platform_context(slug=subdomain)
            return None

        if not org:
            return HttpResponse(
                f"403 Forbidden: Unbekannter Tenant '{subdomain}'.",
                status=403,
                content_type="text/plain",
            )

        set_tenant(org.tenant_id, subdomain)
        set_db_tenant(org.tenant_id)

        request.tenant = org
        request.tenant_id = org.tenant_id
        request.tenant_slug = subdomain

        _sync_platform_context(
            tenant_id=org.tenant_id,
            slug=subdomain,
        )

        return None
