"""Middleware for Risk-Hub."""

import uuid

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

try:
    from platform_context.middleware import HealthBypassMiddleware  # noqa: F401
except ImportError:

    class HealthBypassMiddleware:
        """Shim: platform_context<0.7.0 doesn't include HealthBypassMiddleware."""

        _HEALTH_PATHS = frozenset(["/livez/", "/healthz/"])

        def __init__(self, get_response):
            self.get_response = get_response

        def __call__(self, request: HttpRequest) -> HttpResponse:
            if request.path in self._HEALTH_PATHS and request.method in ("GET", "HEAD"):
                return HttpResponse("ok\n", content_type="text/plain")
            return self.get_response(request)

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
            # Check session for expert/multi-tenant context switch
            session_tenant = request.session.get("active_tenant_id") if hasattr(request, "session") else None
            if session_tenant:
                try:
                    tenant_uuid = uuid.UUID(session_tenant)
                    from tenancy.models import Organization
                    org = Organization.objects.filter(tenant_id=tenant_uuid).first()
                    if org and org.is_active:
                        set_tenant(org.tenant_id, org.slug)
                        set_db_tenant(org.tenant_id)
                        request.tenant = org
                        request.tenant_id = org.tenant_id
                        request.tenant_slug = org.slug
                        _sync_platform_context(tenant_id=org.tenant_id, slug=org.slug)
                        return None
                except (ValueError, TypeError, Exception):
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


_READONLY_WRITE_METHODS = frozenset(["POST", "PUT", "PATCH", "DELETE"])

_READONLY_ALLOWLIST = (
    "/api/v1/internal/",  # billing-hub activate/deactivate callbacks
    "/admin/",  # Django admin (superusers can always access)
    "/livez/",
    "/healthz/",
    "/readyz/",
    "/accounts/logout/",
)


class ReadOnlyTenantMiddleware(MiddlewareMixin):
    """Block write requests when org.is_readonly=True (ADR-118).

    Runs after SubdomainTenantMiddleware — request.tenant must be set.
    Safe paths (billing callbacks, admin, health) are always allowed.
    API clients receive JSON 403; browsers receive plain 403.
    """

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        if request.method not in _READONLY_WRITE_METHODS:
            return None

        if any(request.path.startswith(p) for p in _READONLY_ALLOWLIST):
            return None

        org = getattr(request, "tenant", None)
        if org is None or not getattr(org, "is_readonly", False):
            return None

        delete_at = getattr(org, "gdpr_delete_at", None)
        delete_str = delete_at.strftime("%d.%m.%Y") if delete_at else "unbekannt"
        reason = getattr(org, "deactivation_reason", "") or "Abonnement beendet"

        accept = request.headers.get("Accept", "")
        if "application/json" in accept or request.path.startswith("/api/"):
            return JsonResponse(
                {
                    "error": "read_only",
                    "detail": (
                        f"Ihr Zugang ist deaktiviert: {reason}. "
                        f"Daten werden am {delete_str} gel\u00f6scht."
                    ),
                },
                status=403,
            )

        return HttpResponse(
            (
                f"<h1>Zugang deaktiviert</h1>"
                f"<p>{reason}</p>"
                f"<p>Ihre Daten werden am <strong>{delete_str}</strong> "
                f"automatisch gel\u00f6scht (DSGVO).</p>"
                f"<p>Zum Reaktivieren: "
                f'<a href="https://billing.iil.pet">billing.iil.pet</a></p>'
            ),
            status=403,
            content_type="text/html; charset=utf-8",
        )
