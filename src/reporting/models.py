"""Reporting models."""

import uuid
from django.db import models


class RetentionPolicy(models.Model):
    """Retention policy for documents/exports."""

    class DeleteMode(models.TextChoices):
        SOFT = "soft", "Soft"
        HARD = "hard", "Hard"
        NEVER = "never", "Never"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=120)
    retention_days = models.IntegerField()
    delete_mode = models.CharField(
        max_length=12, choices=DeleteMode.choices,
        default=DeleteMode.SOFT,
    )
    legal_hold_allowed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reporting_retention_policy"

    def __str__(self) -> str:
        return f"{self.name} ({self.retention_days} days)"


class ExportJob(models.Model):
    """Export job for PDF/Excel generation."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    requested_by_user_id = models.UUIDField()
    export_type = models.CharField(max_length=200)
    params_json = models.JSONField(default=dict)
    params_hash = models.CharField(max_length=64)
    status = models.CharField(
        max_length=16, choices=Status.choices,
        default=Status.QUEUED,
    )
    priority = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    output_document_id = models.UUIDField(null=True, blank=True)
    retention_policy = models.ForeignKey(RetentionPolicy, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reporting_export_job"
        indexes = [
            models.Index(
                fields=["tenant_id", "status", "-created_at"],
                name="idx_export_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.export_type} ({self.status})"
