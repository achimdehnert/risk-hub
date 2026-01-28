"""
Request Context
===============

Thread-safe Context für:
- request_id (Correlation ID)
- tenant_id + tenant_slug (Multi-Tenancy)
- user_id (aktueller User)

Verwendung:
    from apps.core.request_context import get_context
    
    ctx = get_context()
    print(ctx.tenant_id)
"""

import contextvars
from dataclasses import dataclass
from uuid import UUID

# Context Variables (thread-safe)
_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
_tenant_id: contextvars.ContextVar[UUID | None] = contextvars.ContextVar(
    "tenant_id", default=None
)
_tenant_slug: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "tenant_slug", default=None
)
_user_id: contextvars.ContextVar[UUID | None] = contextvars.ContextVar(
    "user_id", default=None
)


@dataclass(frozen=True)
class RequestContext:
    """Immutable Request Context."""

    request_id: str | None
    tenant_id: UUID | None
    tenant_slug: str | None
    user_id: UUID | None

    def __bool__(self) -> bool:
        """Context ist 'truthy' wenn Tenant gesetzt."""
        return self.tenant_id is not None


def get_context() -> RequestContext:
    """Aktuellen Request Context abrufen."""
    return RequestContext(
        request_id=_request_id.get(),
        tenant_id=_tenant_id.get(),
        tenant_slug=_tenant_slug.get(),
        user_id=_user_id.get(),
    )


def set_request_id(value: str | None) -> None:
    """Request ID setzen (Correlation ID)."""
    _request_id.set(value)


def set_tenant(tenant_id: UUID | None, tenant_slug: str | None) -> None:
    """Tenant Context setzen."""
    _tenant_id.set(tenant_id)
    _tenant_slug.set(tenant_slug)


def set_user_id(value: UUID | None) -> None:
    """User ID setzen."""
    _user_id.set(value)


def clear_context() -> None:
    """Context zurücksetzen (z.B. nach Request)."""
    _request_id.set(None)
    _tenant_id.set(None)
    _tenant_slug.set(None)
    _user_id.set(None)


class TenantRequired(Exception):
    """Wird geworfen wenn Tenant fehlt aber erforderlich ist."""

    pass


def require_tenant() -> UUID:
    """
    Tenant ID abrufen oder Exception werfen.
    
    Verwendung in Services:
        tenant_id = require_tenant()
    """
    ctx = get_context()
    if ctx.tenant_id is None:
        raise TenantRequired("Operation requires tenant context")
    return ctx.tenant_id
