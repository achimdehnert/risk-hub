"""Tests for outbox models."""

import uuid

import pytest

from outbox.models import OutboxMessage


@pytest.mark.django_db
class TestOutboxMessage:
    def test_should_create_pending_message(self):
        msg = OutboxMessage.objects.create(
            topic="risk.assessment.created",
            payload={"assessment_id": str(uuid.uuid4())},
            aggregate_type="Assessment",
            aggregate_id=uuid.uuid4(),
        )
        assert msg.pk is not None
        assert msg.published_at is None
        assert msg.is_published is False

    def test_should_mark_as_published(self):
        from django.utils import timezone

        msg = OutboxMessage.objects.create(
            topic="risk.hazard.updated",
            payload={"key": "val"},
        )
        msg.published_at = timezone.now()
        msg.save(update_fields=["published_at"])
        assert msg.is_published is True

    def test_should_display_pending_status(self):
        msg = OutboxMessage.objects.create(
            topic="test.event",
            payload={},
        )
        assert "pending" in str(msg)

    def test_should_display_published_status(self):
        from django.utils import timezone

        msg = OutboxMessage.objects.create(
            topic="test.event",
            payload={},
            published_at=timezone.now(),
        )
        assert "published" in str(msg)

    def test_should_allow_null_tenant(self):
        msg = OutboxMessage.objects.create(
            topic="system.event",
            payload={"global": True},
            tenant_id=None,
        )
        assert msg.tenant_id is None

    def test_should_store_json_payload(self):
        payload = {"nested": {"key": "value"}, "list": [1, 2, 3]}
        msg = OutboxMessage.objects.create(
            topic="complex.event",
            payload=payload,
        )
        reloaded = OutboxMessage.objects.get(pk=msg.pk)
        assert reloaded.payload["nested"]["key"] == "value"
        assert reloaded.payload["list"] == [1, 2, 3]
