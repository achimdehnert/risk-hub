"""Approval workflow models for multi-step review processes."""

import uuid

from django.db import models
from django.utils import timezone

from identity.models import User


class ApprovalWorkflow(models.Model):
    """Configurable approval workflow template per tenant."""

    class WorkflowType(models.TextChoices):
        EX_CONCEPT = "ex_concept", "Ex-Schutz-Konzept"
        RISK_ASSESSMENT = "risk_assessment", "Risikobewertung"
        PROTECTION_MEASURE = "protection_measure", "Schutzmaßnahme"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(db_index=True)
    workflow_type = models.CharField(
        max_length=30,
        choices=WorkflowType.choices,
        db_index=True,
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "approvals_workflow"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "workflow_type"],
                condition=models.Q(is_active=True),
                name="uq_active_workflow_per_type",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_workflow_type_display()})"


class ApprovalStep(models.Model):
    """A single step in an approval workflow."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    order = models.IntegerField(
        help_text="Reihenfolge der Freigabestufe (1, 2, 3...)"
    )
    name = models.CharField(
        max_length=200,
        help_text="z.B. 'Fachliche Prüfung', 'Freigabe GF'"
    )
    required_permission = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Permission code required to approve this step",
    )
    require_comment = models.BooleanField(
        default=False,
        help_text="Kommentar bei Freigabe erforderlich",
    )

    class Meta:
        db_table = "approvals_step"
        ordering = ["workflow", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "order"],
                name="uq_step_order",
            ),
        ]

    def __str__(self) -> str:
        return f"Step {self.order}: {self.name}"


class ApprovalRequest(models.Model):
    """A concrete approval request for a specific entity."""

    class Status(models.TextChoices):
        PENDING = "pending", "Ausstehend"
        IN_REVIEW = "in_review", "In Prüfung"
        APPROVED = "approved", "Freigegeben"
        REJECTED = "rejected", "Abgelehnt"
        WITHDRAWN = "withdrawn", "Zurückgezogen"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(db_index=True)
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.PROTECT,
        related_name="requests",
    )

    # Polymorphic entity reference
    entity_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="z.B. 'explosionsschutz.ExplosionConcept'",
    )
    entity_id = models.UUIDField(db_index=True)

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    current_step = models.IntegerField(
        default=1,
        help_text="Currently active step order number",
    )

    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="approval_requests",
    )
    requested_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "approvals_request"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status", "-requested_at"],
                name="approval_req_status_idx",
            ),
            models.Index(
                fields=["entity_type", "entity_id"],
                name="approval_req_entity_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.entity_type}:{self.entity_id} "
            f"({self.get_status_display()})"
        )


class ApprovalDecision(models.Model):
    """A decision (approve/reject) for a specific step."""

    class Outcome(models.TextChoices):
        APPROVED = "approved", "Freigegeben"
        REJECTED = "rejected", "Abgelehnt"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    request = models.ForeignKey(
        ApprovalRequest,
        on_delete=models.CASCADE,
        related_name="decisions",
    )
    step = models.ForeignKey(
        ApprovalStep,
        on_delete=models.PROTECT,
        related_name="decisions",
    )
    outcome = models.CharField(
        max_length=10, choices=Outcome.choices
    )
    comment = models.TextField(blank=True, default="")
    decided_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
    )
    decided_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "approvals_decision"
        ordering = ["decided_at"]

    def __str__(self) -> str:
        return (
            f"Step {self.step.order}: "
            f"{self.get_outcome_display()} by {self.decided_by}"
        )
