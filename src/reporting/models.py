"""Reporting models."""

import uuid
from django.db import models


class RetentionPolicy(models.Model):
    """Retention policy for documents/exports."""
    
    DELETE_SOFT = "soft"
    DELETE_HARD = "hard"
    DELETE_NEVER = "never"
    DELETE_CHOICES = [(DELETE_SOFT, "Soft"), (DELETE_HARD, "Hard"), (DELETE_NEVER, "Never")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=120)
    retention_days = models.IntegerField()
    delete_mode = models.CharField(max_length=12, choices=DELETE_CHOICES, default=DELETE_SOFT)
    legal_hold_allowed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reporting_retention_policy"

    def __str__(self) -> str:
        return f"{self.name} ({self.retention_days} days)"


class ExportJob(models.Model):
    """Export job for PDF/Excel generation."""
    
    STATUS_QUEUED = "queued"
    STATUS_RUNNING = "running"
    STATUS_DONE = "done"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_RUNNING, "Running"),
        (STATUS_DONE, "Done"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    requested_by_user_id = models.UUIDField()
    export_type = models.CharField(max_length=200)
    params_json = models.JSONField(default=dict)
    params_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_QUEUED)
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
            models.Index(fields=["tenant_id", "status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.export_type} ({self.status})"
