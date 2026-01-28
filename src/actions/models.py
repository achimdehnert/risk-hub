"""Action item models."""

import uuid
from django.db import models


class ActionItem(models.Model):
    """Action item / Maßnahme."""
    
    STATUS_CHOICES = [
        ("open", "Offen"),
        ("in_progress", "In Bearbeitung"),
        ("completed", "Erledigt"),
        ("cancelled", "Abgebrochen"),
    ]
    
    PRIORITY_CHOICES = [
        (1, "Niedrig"),
        (2, "Mittel"),
        (3, "Hoch"),
        (4, "Kritisch"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)
    
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
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "due_date"]),
        ]

    def __str__(self) -> str:
        return self.title
