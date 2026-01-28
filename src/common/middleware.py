"""Middleware for Risk-Hub."""

import uuid
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

from bfagent_core import set_request_id, set_tenant, set_user_id, set_db_tenant


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
        base_domain = getattr(settings, "TENANT_BASE_DOMAIN", "localhost")
        allow_localhost = getattr(settings, "TENANT_ALLOW_LOCALHOST", False)
        
        subdomain = _parse_subdomain(request.get_host(), base_domain)
        
        if not subdomain:
            if allow_localhost and request.path.startswith("/admin/"):
                set_tenant(None, None)
                set_db_tenant(None)
                return None
            return HttpResponseForbidden("Missing tenant subdomain")
        
        # Look up tenant
        from tenancy.models import Organization
        org = Organization.objects.filter(slug=subdomain).first()
        
        if not org:
            return HttpResponseForbidden(f"Unknown tenant: {subdomain}")
        
        set_tenant(org.tenant_id, subdomain)
        set_db_tenant(org.tenant_id)
        
        request.tenant = org
        request.tenant_id = org.tenant_id
        request.tenant_slug = subdomain
        
        return None
