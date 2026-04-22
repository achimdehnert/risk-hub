"""Audit query helpers (ADR-041)."""

from __future__ import annotations


def get_audit_events(tenant_id):
    """Return AuditEvent queryset for a tenant."""
    from audit.models import AuditEvent

    return AuditEvent.objects.filter(tenant_id=tenant_id)


def get_audit_resource_types(tenant_id):
    """Return distinct resource_type values for a tenant (for filter dropdowns)."""
    from audit.models import AuditEvent

    return (
        AuditEvent.objects.filter(tenant_id=tenant_id)
        .values_list("resource_type", flat=True)
        .distinct()[:50]
    )
