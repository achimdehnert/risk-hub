"""
Thread-local context management for Risk-Hub.

Provides tenant isolation, user tracking, and request context
without external dependencies.
"""

import contextvars
import uuid
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

# Context variables (thread-safe)
_tenant_id: contextvars.ContextVar[Optional[UUID]] = contextvars.ContextVar(
    "tenant_id", default=None
)
_tenant_slug: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "tenant_slug", default=None
)
_user_id: contextvars.ContextVar[Optional[UUID]] = contextvars.ContextVar(
    "user_id", default=None
)
_request_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)


@dataclass(frozen=True)
class RequestContext:
    """Immutable snapshot of current request context."""

    tenant_id: Optional[UUID]
    tenant_slug: Optional[str]
    user_id: Optional[UUID]
    request_id: Optional[str]


def get_context() -> RequestContext:
    """Get current request context."""
    return RequestContext(
        tenant_id=_tenant_id.get(),
        tenant_slug=_tenant_slug.get(),
        user_id=_user_id.get(),
        request_id=_request_id.get(),
    )


def set_tenant(tenant_id: Optional[UUID], tenant_slug: Optional[str]) -> None:
    """Set current tenant context."""
    _tenant_id.set(tenant_id)
    _tenant_slug.set(tenant_slug)


def set_user_id(user_id: Optional[UUID]) -> None:
    """Set current user ID."""
    _user_id.set(user_id)


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set request ID. Generates one if not provided."""
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    _request_id.set(request_id)
    return request_id


def set_db_tenant(tenant_id: Optional[UUID]) -> None:
    """
    Set tenant for database queries.
    
    In this implementation, this is a no-op as we use explicit
    tenant_id filtering. Kept for API compatibility.
    """
    pass


def clear_context() -> None:
    """Clear all context variables."""
    _tenant_id.set(None)
    _tenant_slug.set(None)
    _user_id.set(None)
    _request_id.set(None)


# =============================================================================
# EVENT EMISSION HELPERS
# =============================================================================

def emit_audit_event(
    event_type: str,
    resource_type: str,
    resource_id: Optional[UUID] = None,
    details: Optional[dict] = None,
) -> None:
    """
    Emit an audit event.
    
    Creates an AuditEvent record for tracking user actions.
    """
    from audit.models import AuditEvent

    ctx = get_context()
    AuditEvent.objects.create(
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        request_id=ctx.request_id,
    )


def emit_outbox_event(
    topic: str,
    payload: dict,
    aggregate_type: Optional[str] = None,
    aggregate_id: Optional[UUID] = None,
) -> None:
    """
    Emit an outbox event for reliable event publishing.
    
    Uses the transactional outbox pattern to ensure events
    are published exactly once.
    """
    from outbox.models import OutboxMessage

    ctx = get_context()
    OutboxMessage.objects.create(
        tenant_id=ctx.tenant_id,
        topic=topic,
        payload=payload,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
    )
