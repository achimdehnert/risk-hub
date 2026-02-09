"""Action item models."""

import uuid
from django.db import models


class ActionItem(models.Model):
    """Action item / Maßnahme."""

    class Status(models.TextChoices):
        OPEN = "open", "Offen"
        IN_PROGRESS = "in_progress", "In Bearbeitung"
        COMPLETED = "completed", "Erledigt"
        CANCELLED = "cancelled", "Abgebrochen"

    class Priority(models.IntegerChoices):
        LOW = 1, "Niedrig"
        MEDIUM = 2, "Mittel"
        HIGH = 3, "Hoch"
        CRITICAL = 4, "Kritisch"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.OPEN,
    )
    priority = models.IntegerField(
        choices=Priority.choices, default=Priority.MEDIUM,
    )
    
    due_date = models.DateField(null=True, blank=True)
    assigned_to_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    # Link to assessment/hazard
    assessment_id = models.UUIDField(null=True, blank=True, db_index=True)
    hazard_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "actions_action_item"
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "title"], name="uq_action_title_per_tenant"),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_action_tenant_status",
            ),
            models.Index(
                fields=["tenant_id", "due_date"],
                name="idx_action_tenant_due",
            ),
        ]

    def __str__(self) -> str:
        return self.title
