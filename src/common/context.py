"""
Thread-local context management for Risk-Hub.

Provides tenant isolation, user tracking, and request context
without external dependencies.
"""

from __future__ import annotations

import contextvars
import uuid
from dataclasses import dataclass
from uuid import UUID

# Context variables (thread-safe)
_tenant_id: contextvars.ContextVar[UUID | None] = contextvars.ContextVar(
    "tenant_id", default=None
)
_tenant_slug: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "tenant_slug", default=None
)
_user_id: contextvars.ContextVar[UUID | None] = contextvars.ContextVar(
    "user_id", default=None
)
_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


@dataclass(frozen=True)
class RequestContext:
    """Immutable snapshot of current request context."""

    tenant_id: UUID | None
    tenant_slug: str | None
    user_id: UUID | None
    request_id: str | None


def get_context() -> RequestContext:
    """Get current request context."""
    return RequestContext(
        tenant_id=_tenant_id.get(),
        tenant_slug=_tenant_slug.get(),
        user_id=_user_id.get(),
        request_id=_request_id.get(),
    )


def set_tenant(tenant_id: UUID | None, tenant_slug: str | None) -> None:
    """Set current tenant context."""
    _tenant_id.set(tenant_id)
    _tenant_slug.set(tenant_slug)


def set_user_id(user_id: UUID | None) -> None:
    """Set current user ID."""
    _user_id.set(user_id)


def set_request_id(request_id: str | None = None) -> str:
    """Set request ID. Generates one if not provided."""
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    _request_id.set(request_id)
    return request_id


def set_db_tenant(tenant_id: UUID | None) -> None:
    """Set PostgreSQL session variable for RLS (ADR-003 §4.3).

    Sets ``app.tenant_id`` via ``SET LOCAL`` so RLS policies
    can enforce tenant isolation at the DB level.
    """
    from django.db import connection

    if tenant_id is not None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SET LOCAL app.tenant_id = %s", [str(tenant_id)],
            )
    else:
        with connection.cursor() as cursor:
            cursor.execute("RESET app.tenant_id")


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
    tenant_id: UUID | None = None,
    category: str = "",
    action: str = "",
    entity_type: str = "",
    entity_id: UUID | None = None,
    payload: dict | None = None,
    user_id: UUID | None = None,
) -> None:
    """
    Emit an audit event.

    Creates an AuditEvent record for tracking user actions.
    Falls back to context for tenant_id/user_id if not provided.
    """
    from audit.models import AuditEvent

    ctx = get_context()
    AuditEvent.objects.create(
        tenant_id=tenant_id or ctx.tenant_id,
        user_id=user_id or ctx.user_id,
        event_type=action or "other",
        resource_type=entity_type or category,
        resource_id=entity_id,
        details=payload or {},
        request_id=ctx.request_id,
    )


def emit_outbox_event(
    topic: str = "",
    payload: dict | None = None,
    aggregate_type: str | None = None,
    aggregate_id: UUID | None = None,
    tenant_id: UUID | None = None,
) -> None:
    """
    Emit an outbox event for reliable event publishing.

    Uses the transactional outbox pattern to ensure events
    are published exactly once.
    Falls back to context for tenant_id if not provided.
    """
    from outbox.models import OutboxMessage

    ctx = get_context()
    OutboxMessage.objects.create(
        tenant_id=tenant_id or ctx.tenant_id,
        topic=topic,
        payload=payload or {},
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
    )
