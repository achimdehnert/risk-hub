"""Initial migration for approvals app."""

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ApprovalWorkflow",
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
                    "workflow_type",
                    models.CharField(
                        choices=[
                            ("ex_concept", "Ex-Schutz-Konzept"),
                            ("risk_assessment", "Risikobewertung"),
                            (
                                "protection_measure",
                                "Schutzmaßnahme",
                            ),
                        ],
                        db_index=True,
                        max_length=30,
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=200),
                ),
                (
                    "description",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
            ],
            options={
                "db_table": "approvals_workflow",
            },
        ),
        migrations.CreateModel(
            name="ApprovalStep",
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
                    "order",
                    models.IntegerField(
                        help_text="Reihenfolge der Freigabestufe",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=200),
                ),
                (
                    "required_permission",
                    models.CharField(
                        blank=True, default="", max_length=100,
                    ),
                ),
                (
                    "require_comment",
                    models.BooleanField(default=False),
                ),
                (
                    "workflow",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="steps",
                        to="approvals.approvalworkflow",
                    ),
                ),
            ],
            options={
                "db_table": "approvals_step",
                "ordering": ["workflow", "order"],
            },
        ),
        migrations.CreateModel(
            name="ApprovalRequest",
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
                    "entity_type",
                    models.CharField(
                        db_index=True, max_length=100,
                    ),
                ),
                (
                    "entity_id",
                    models.UUIDField(db_index=True),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Ausstehend"),
                            ("in_review", "In Prüfung"),
                            ("approved", "Freigegeben"),
                            ("rejected", "Abgelehnt"),
                            ("withdrawn", "Zurückgezogen"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=15,
                    ),
                ),
                (
                    "current_step",
                    models.IntegerField(default=1),
                ),
                (
                    "requested_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        blank=True, null=True,
                    ),
                ),
                (
                    "workflow",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="requests",
                        to="approvals.approvalworkflow",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="approval_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "approvals_request",
                "ordering": ["-requested_at"],
            },
        ),
        migrations.CreateModel(
            name="ApprovalDecision",
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
                    "outcome",
                    models.CharField(
                        choices=[
                            ("approved", "Freigegeben"),
                            ("rejected", "Abgelehnt"),
                        ],
                        max_length=10,
                    ),
                ),
                (
                    "comment",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "decided_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="decisions",
                        to="approvals.approvalrequest",
                    ),
                ),
                (
                    "step",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="decisions",
                        to="approvals.approvalstep",
                    ),
                ),
                (
                    "decided_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "approvals_decision",
                "ordering": ["decided_at"],
            },
        ),
        # Constraints
        migrations.AddConstraint(
            model_name="approvalworkflow",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_active=True),
                fields=("tenant_id", "workflow_type"),
                name="uq_active_workflow_per_type",
            ),
        ),
        migrations.AddConstraint(
            model_name="approvalstep",
            constraint=models.UniqueConstraint(
                fields=("workflow", "order"),
                name="uq_step_order",
            ),
        ),
        # Indexes
        migrations.AddIndex(
            model_name="approvalrequest",
            index=models.Index(
                fields=["tenant_id", "status", "-requested_at"],
                name="approval_req_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="approvalrequest",
            index=models.Index(
                fields=["entity_type", "entity_id"],
                name="approval_req_entity_idx",
            ),
        ),
    ]
