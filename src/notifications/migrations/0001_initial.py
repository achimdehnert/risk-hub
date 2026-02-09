"""Initial migration for notifications app."""

import uuid

import django.db.models
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Notification",
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
                (
                    "tenant_id",
                    models.UUIDField(db_index=True),
                ),
                (
                    "recipient_id",
                    models.UUIDField(
                        blank=True,
                        db_index=True,
                        help_text="Target user; NULL = all tenant users",
                        null=True,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("inspection_due", "Prüfung fällig"),
                            ("inspection_overdue", "Prüfung überfällig"),
                            ("measure_due", "Maßnahme fällig"),
                            ("concept_status", "Konzept-Status"),
                            ("sds_expiring", "SDB läuft ab"),
                            ("approval_required", "Freigabe erforderlich"),
                            ("system", "System"),
                        ],
                        db_index=True,
                        max_length=30,
                    ),
                ),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("info", "Information"),
                            ("warning", "Warnung"),
                            ("critical", "Kritisch"),
                        ],
                        default="info",
                        max_length=10,
                    ),
                ),
                (
                    "title",
                    models.CharField(max_length=200),
                ),
                (
                    "message",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "entity_type",
                    models.CharField(
                        blank=True, default="", max_length=100,
                    ),
                ),
                (
                    "entity_id",
                    models.UUIDField(blank=True, null=True),
                ),
                (
                    "action_url",
                    models.CharField(
                        blank=True, default="", max_length=500,
                    ),
                ),
                (
                    "is_read",
                    models.BooleanField(
                        db_index=True, default=False,
                    ),
                ),
                (
                    "read_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        db_index=True,
                        default=django.utils.timezone.now,
                    ),
                ),
            ],
            options={
                "db_table": "notifications_notification",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="NotificationPreference",
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
                (
                    "tenant_id",
                    models.UUIDField(db_index=True),
                ),
                (
                    "user_id",
                    models.UUIDField(db_index=True),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("inspection_due", "Prüfung fällig"),
                            ("inspection_overdue", "Prüfung überfällig"),
                            ("measure_due", "Maßnahme fällig"),
                            ("concept_status", "Konzept-Status"),
                            ("sds_expiring", "SDB läuft ab"),
                            ("approval_required", "Freigabe erforderlich"),
                            ("system", "System"),
                        ],
                        max_length=30,
                    ),
                ),
                (
                    "channel",
                    models.CharField(
                        choices=[
                            ("in_app", "In-App"),
                            ("email", "E-Mail"),
                            ("both", "Beides"),
                            ("none", "Keine"),
                        ],
                        default="both",
                        max_length=10,
                    ),
                ),
                (
                    "reminder_days",
                    models.JSONField(
                        default=list,
                        help_text=(
                            "Erinnerung X Tage vorher,"
                            " z.B. [30, 7, 3, 1]"
                        ),
                    ),
                ),
            ],
            options={
                "db_table": "notifications_preference",
            },
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["tenant_id", "is_read", "-created_at"],
                name="notif_unread_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["tenant_id", "category", "-created_at"],
                name="notif_category_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="notificationpreference",
            constraint=models.UniqueConstraint(
                fields=("tenant_id", "user_id", "category"),
                name="uq_notif_pref_user_cat",
            ),
        ),
    ]
