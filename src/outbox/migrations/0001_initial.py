"""Initial migration for outbox app."""

import uuid

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    """Create OutboxMessage model."""

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="OutboxMessage",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.UUIDField(blank=True, db_index=True, null=True)),
                (
                    "topic",
                    models.CharField(
                        db_index=True,
                        help_text="Event topic/channel name",
                        max_length=255,
                    ),
                ),
                (
                    "payload",
                    models.JSONField(
                        default=dict,
                        help_text="Event payload as JSON",
                    ),
                ),
                (
                    "aggregate_type",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Type of aggregate (e.g., 'Risk', 'Action')",
                        max_length=100,
                    ),
                ),
                (
                    "aggregate_id",
                    models.UUIDField(
                        blank=True,
                        help_text="ID of the related aggregate",
                        null=True,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        db_index=True,
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "published_at",
                    models.DateTimeField(
                        blank=True,
                        db_index=True,
                        help_text="When the message was published (null = pending)",
                        null=True,
                    ),
                ),
            ],
            options={
                "db_table": "outbox_message",
                "ordering": ["created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="outboxmessage",
            index=models.Index(
                fields=["published_at", "created_at"],
                name="outbox_pending_idx",
            ),
        ),
    ]
