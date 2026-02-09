"""Tests for audit log views and CSV export."""

import uuid

import pytest

from audit.models import AuditEvent


TENANT_ID = uuid.uuid4()


@pytest.mark.django_db
class TestAuditEvent:
    """Test AuditEvent model."""

    def test_should_create_event(self):
        ev = AuditEvent.objects.create(
            tenant_id=TENANT_ID,
            event_type=AuditEvent.EventType.CREATE,
            resource_type="Risk",
            resource_id=uuid.uuid4(),
        )
        assert ev.pk is not None
        assert ev.event_type == "create"

    def test_should_store_json_details(self):
        ev = AuditEvent.objects.create(
            tenant_id=TENANT_ID,
            event_type=AuditEvent.EventType.UPDATE,
            resource_type="Equipment",
            details={"field": "name", "old": "A", "new": "B"},
        )
        assert ev.details["field"] == "name"

    def test_should_order_newest_first(self):
        AuditEvent.objects.create(
            tenant_id=TENANT_ID,
            event_type=AuditEvent.EventType.VIEW,
            resource_type="Doc",
        )
        ev2 = AuditEvent.objects.create(
            tenant_id=TENANT_ID,
            event_type=AuditEvent.EventType.EXPORT,
            resource_type="Doc",
        )
        first = AuditEvent.objects.filter(
            tenant_id=TENANT_ID,
        ).first()
        assert first.pk == ev2.pk

    def test_should_filter_by_event_type(self):
        AuditEvent.objects.create(
            tenant_id=TENANT_ID,
            event_type=AuditEvent.EventType.CREATE,
            resource_type="Risk",
        )
        AuditEvent.objects.create(
            tenant_id=TENANT_ID,
            event_type=AuditEvent.EventType.DELETE,
            resource_type="Risk",
        )
        creates = AuditEvent.objects.filter(
            tenant_id=TENANT_ID, event_type="create",
        )
        assert creates.count() == 1

    def test_should_filter_by_resource_type(self):
        AuditEvent.objects.create(
            tenant_id=TENANT_ID,
            event_type=AuditEvent.EventType.CREATE,
            resource_type="Equipment",
        )
        AuditEvent.objects.create(
            tenant_id=TENANT_ID,
            event_type=AuditEvent.EventType.CREATE,
            resource_type="Risk",
        )
        equip = AuditEvent.objects.filter(
            tenant_id=TENANT_ID,
            resource_type="Equipment",
        )
        assert equip.count() == 1

    def test_should_display_string(self):
        ev = AuditEvent.objects.create(
            tenant_id=TENANT_ID,
            event_type=AuditEvent.EventType.APPROVE,
            resource_type="Concept",
        )
        s = str(ev)
        assert "approve" in s
        assert "Concept" in s
