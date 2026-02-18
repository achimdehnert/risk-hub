"""
Audit Service
=============

Service für Audit Event Emission.

Verwendung:
    from apps.audit.services import emit_audit_event
    
    emit_audit_event(
        category="risk.assessment",
        action="created",
        entity_type="risk.Assessment",
        entity_id=assessment.id,
        payload={"title": assessment.title},
    )
"""

from uuid import UUID

from apps.audit.models import AuditEvent
from apps.core.request_context import get_context, require_tenant


def emit_audit_event(
    *,
    category: str,
    action: str,
    entity_type: str,
    entity_id: UUID,
    payload: dict | None = None,
    tenant_id: UUID | None = None,
) -> AuditEvent:
    """
    Audit Event erstellen.
    
    Sollte innerhalb der gleichen DB-Transaktion wie die
    fachliche Operation aufgerufen werden.
    """
    ctx = get_context()
    
    if tenant_id is None:
        tenant_id = require_tenant()
    
    event = AuditEvent.objects.create(
        tenant_id=tenant_id,
        actor_user_id=ctx.user_id,
        category=category,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload or {},
        request_id=ctx.request_id,
    )
    
    return event
