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
            # TODO: Forward to actual message broker here
            msg.published_at = timezone.now()
            msg.save(update_fields=["published_at"])
            published += 1
        except Exception:
            logger.exception(
                "Failed to publish outbox message %s", msg.id
            )

    return {"published": published, "pending": pending.count()}
