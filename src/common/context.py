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
_tenant_id: contextvars.ContextVar[UUID | None] = contextvars.ContextVar("tenant_id", default=None)
_tenant_slug: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "tenant_slug", default=None
)
_user_id: contextvars.ContextVar[UUID | None] = contextvars.ContextVar("user_id", default=None)
_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


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

    Uses session-scoped ``SET`` (not ``SET LOCAL``) so the
    variable persists across autocommit queries until the
    next request resets it via middleware.
    No-op on SQLite (test environment).

    Also resets ``app.is_service_account`` to ``false`` — normal
    request context is never a service account.
    """
    from django.db import connection

    if connection.vendor != "postgresql":
        return

    with connection.cursor() as cursor:
        if tenant_id is not None:
            cursor.execute(
                "SET app.tenant_id = %s",
                [str(tenant_id)],
            )
        else:
            cursor.execute("RESET app.tenant_id")
        cursor.execute("SET app.is_service_account = 'false'")


def set_db_service_account(enabled: bool = True) -> None:
    """Set PostgreSQL session variable for service-account RLS bypass (ADR-161 §3.2).

    Service accounts may INSERT into global_sds tables.
    Normal users may only SELECT.

    Usage in Celery tasks / management commands::

        from common.context import set_db_service_account
        set_db_service_account(True)
        try:
            GlobalSubstance.objects.create(...)
        finally:
            set_db_service_account(False)
    """
    from django.db import connection

    if connection.vendor != "postgresql":
        return

    with connection.cursor() as cursor:
        cursor.execute(
            "SET app.is_service_account = %s",
            ["true" if enabled else "false"],
        )


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
