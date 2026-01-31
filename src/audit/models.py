"""
Audit models for tracking user actions and system events.

Provides comprehensive audit logging for compliance and debugging.
"""

import uuid

from django.db import models
from django.utils import timezone


class AuditEvent(models.Model):
    """
    Audit event for tracking user actions.

    Records all significant actions for compliance, debugging,
    and analytics purposes.
    """

    class EventType(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        VIEW = "view", "View"
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"
        EXPORT = "export", "Export"
        IMPORT = "import", "Import"
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True, null=True, blank=True)
    user_id = models.UUIDField(db_index=True, null=True, blank=True)

    event_type = models.CharField(
        max_length=50,
        choices=EventType.choices,
        default=EventType.OTHER,
        db_index=True,
    )
    resource_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Type of resource (e.g., 'Risk', 'Action', 'Document')",
    )
    resource_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="ID of the affected resource",
    )

    details = models.JSONField(
        default=dict,
        help_text="Additional event details as JSON",
    )

    request_id = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Request ID for correlation",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Client IP address",
    )
    user_agent = models.TextField(
        blank=True,
        default="",
        help_text="Client user agent",
    )

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "audit_event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "created_at"],
                name="audit_tenant_time_idx",
            ),
            models.Index(
                fields=["resource_type", "resource_id"],
                name="audit_resource_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} {self.resource_type} @ {self.created_at}"
