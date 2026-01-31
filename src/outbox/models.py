"""
Outbox models for transactional event publishing.

Implements the Transactional Outbox Pattern for reliable
event publishing with exactly-once semantics.
"""

import uuid

from django.db import models
from django.utils import timezone


class OutboxMessage(models.Model):
    """
    Transactional outbox message for reliable event publishing.

    Messages are written to this table within the same transaction
    as the business operation, then published asynchronously by
    the outbox publisher worker.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True, null=True, blank=True)

    topic = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Event topic/channel name",
    )
    payload = models.JSONField(
        default=dict,
        help_text="Event payload as JSON",
    )

    aggregate_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Type of aggregate (e.g., 'Risk', 'Action')",
    )
    aggregate_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the related aggregate",
    )

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When the message was published (null = pending)",
    )

    class Meta:
        db_table = "outbox_message"
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["published_at", "created_at"],
                name="outbox_pending_idx",
            ),
        ]

    def __str__(self) -> str:
        status = "published" if self.published_at else "pending"
        return f"{self.topic} ({status})"

    @property
    def is_published(self) -> bool:
        return self.published_at is not None
