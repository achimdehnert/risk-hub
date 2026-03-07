"""Celery tasks for outbox processing."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="outbox.tasks.process_outbox")
def process_outbox(batch_size: int = 50) -> dict:
    """
    Publish pending outbox messages.

    Marks messages as published after processing. In a full
    implementation this would forward to a message broker
    (e.g. Redis Streams, RabbitMQ). For now it marks them
    as published and logs the topic.
    """
    from outbox.models import OutboxMessage

    pending = OutboxMessage.objects.filter(
        published_at__isnull=True,
    ).order_by("created_at")[:batch_size]

    published = 0
    for msg in pending:
        try:
            logger.info(
                "Publishing outbox message: %s (topic=%s)",
                msg.id,
                msg.topic,
            )
            _dispatch_outbox_message(msg)
            msg.published_at = timezone.now()
            msg.save(update_fields=["published_at"])
            published += 1
        except Exception:
            logger.exception("Failed to publish outbox message %s", msg.id)

    return {"published": published, "pending": pending.count()}


def _dispatch_outbox_message(msg) -> None:
    """
    Route outbox message to in-app notification service for known topics.
    Unknown topics are logged and silently dropped (no external broker yet).
    """
    topic = msg.topic
    payload = msg.payload or {}

    if topic in (
        "inspection.overdue",
        "inspection.due_soon",
        "sds.expiring",
        "measure.due",
        "concept.status_changed",
        "approval.required",
    ):
        _create_notification_from_outbox(msg, topic, payload)
    else:
        logger.debug("[Outbox] No handler for topic=%s, skipping dispatch", topic)


def _create_notification_from_outbox(msg, topic: str, payload: dict) -> None:
    """Create in-app Notification from outbox message payload."""
    try:
        from notifications.models import Notification
        from notifications.services import create_notification

        title = payload.get("title", topic)
        message = payload.get("message", "")
        severity = payload.get("severity", Notification.Severity.INFO)
        category_map = {
            "inspection.overdue": Notification.Category.INSPECTION_OVERDUE,
            "inspection.due_soon": Notification.Category.INSPECTION_DUE,
            "sds.expiring": Notification.Category.SDS_EXPIRING,
            "measure.due": Notification.Category.MEASURE_DUE,
            "concept.status_changed": Notification.Category.CONCEPT_STATUS,
            "approval.required": Notification.Category.APPROVAL_REQUIRED,
        }
        category = category_map.get(topic, Notification.Category.SYSTEM)
        create_notification(
            tenant_id=msg.tenant_id,
            title=title,
            message=message,
            category=category,
            severity=severity,
            entity_type=msg.aggregate_type or "",
            entity_id=msg.aggregate_id,
            action_url=payload.get("action_url", ""),
        )
        logger.debug("[Outbox] Notification created for topic=%s", topic)
    except Exception:
        logger.exception("[Outbox] Failed to create notification for %s", topic)
