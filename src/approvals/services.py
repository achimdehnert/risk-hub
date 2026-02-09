"""Approval workflow service — submit, decide, advance steps."""

import logging
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from common.context import emit_audit_event
from approvals.models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStep,
    ApprovalWorkflow,
)
from permissions.authz import require_permission

logger = logging.getLogger(__name__)


@transaction.atomic
def submit_for_approval(
    tenant_id: UUID,
    entity_type: str,
    entity_id: UUID,
    user_id: UUID | None = None,
) -> ApprovalRequest:
    """
    Submit an entity for approval using the active workflow.

    Raises ValueError if no active workflow exists for the entity type.
    """
    # Map entity_type to workflow_type
    wf_type = _entity_to_workflow_type(entity_type)

    workflow = ApprovalWorkflow.objects.filter(
        tenant_id=tenant_id,
        workflow_type=wf_type,
        is_active=True,
    ).first()

    if not workflow:
        raise ValueError(
            f"Kein aktiver Workflow für {entity_type}. "
            "Bitte Workflow konfigurieren."
        )

    # Check if there's already a pending request
    existing = ApprovalRequest.objects.filter(
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        status__in=[
            ApprovalRequest.Status.PENDING,
            ApprovalRequest.Status.IN_REVIEW,
        ],
    ).first()

    if existing:
        raise ValueError(
            "Es läuft bereits ein Freigabeprozess für dieses Objekt."
        )

    request = ApprovalRequest.objects.create(
        tenant_id=tenant_id,
        workflow=workflow,
        entity_type=entity_type,
        entity_id=entity_id,
        status=ApprovalRequest.Status.IN_REVIEW,
        current_step=1,
        requested_by_id=user_id,
    )

    emit_audit_event(
        tenant_id=tenant_id,
        category="approval",
        action="submitted",
        entity_type=entity_type,
        entity_id=entity_id,
        payload={
            "request_id": str(request.id),
            "workflow": workflow.name,
        },
        user_id=user_id,
    )

    logger.info(
        "Approval submitted: %s %s (workflow=%s)",
        entity_type, entity_id, workflow.name,
    )
    return request


@transaction.atomic
def decide(
    request_id: UUID,
    outcome: str,
    user_id: UUID,
    tenant_id: UUID,
    comment: str = "",
) -> ApprovalDecision:
    """
    Record a decision (approve/reject) for the current step.

    If approved and more steps remain, advances to next step.
    If approved and last step, marks request as approved.
    If rejected, marks request as rejected.
    """
    request = ApprovalRequest.objects.select_related(
        "workflow"
    ).get(
        id=request_id,
        tenant_id=tenant_id,
    )

    if request.status not in (
        ApprovalRequest.Status.PENDING,
        ApprovalRequest.Status.IN_REVIEW,
    ):
        raise ValueError(
            f"Freigabe nicht möglich: Status ist {request.get_status_display()}"
        )

    # Get the current step
    step = ApprovalStep.objects.get(
        workflow=request.workflow,
        order=request.current_step,
    )

    # Check permission if step requires one
    if step.required_permission:
        require_permission(step.required_permission)

    # Validate comment requirement
    if step.require_comment and not comment.strip():
        raise ValueError("Kommentar ist für diese Stufe erforderlich.")

    # Record the decision
    decision = ApprovalDecision.objects.create(
        request=request,
        step=step,
        outcome=outcome,
        comment=comment,
        decided_by_id=user_id,
    )

    if outcome == ApprovalDecision.Outcome.REJECTED:
        request.status = ApprovalRequest.Status.REJECTED
        request.completed_at = timezone.now()
        request.save(update_fields=["status", "completed_at"])
        _notify_rejection(request, decision)
    elif outcome == ApprovalDecision.Outcome.APPROVED:
        # Check if there are more steps
        next_step = ApprovalStep.objects.filter(
            workflow=request.workflow,
            order__gt=request.current_step,
        ).order_by("order").first()

        if next_step:
            request.current_step = next_step.order
            request.save(update_fields=["current_step"])
        else:
            # All steps approved — mark as fully approved
            request.status = ApprovalRequest.Status.APPROVED
            request.completed_at = timezone.now()
            request.save(update_fields=["status", "completed_at"])
            _on_fully_approved(request)

    emit_audit_event(
        tenant_id=tenant_id,
        category="approval",
        action=f"step_{outcome}",
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        payload={
            "request_id": str(request.id),
            "step": step.name,
            "step_order": step.order,
            "outcome": outcome,
            "comment": comment[:200],
        },
        user_id=user_id,
    )

    return decision


def get_pending_approvals(
    tenant_id: UUID,
    user_id: UUID | None = None,
) -> list[ApprovalRequest]:
    """Get all pending approval requests for a tenant."""
    return list(
        ApprovalRequest.objects.filter(
            tenant_id=tenant_id,
            status=ApprovalRequest.Status.IN_REVIEW,
        ).select_related("workflow", "requested_by")
        .order_by("-requested_at")
    )


def get_approval_history(
    entity_type: str,
    entity_id: UUID,
    tenant_id: UUID,
) -> list[ApprovalRequest]:
    """Get approval history for a specific entity."""
    return list(
        ApprovalRequest.objects.filter(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
        ).prefetch_related("decisions__step", "decisions__decided_by")
        .order_by("-requested_at")
    )


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _entity_to_workflow_type(entity_type: str) -> str:
    """Map entity_type string to workflow type."""
    mapping = {
        "explosionsschutz.ExplosionConcept": "ex_concept",
        "risk.Assessment": "risk_assessment",
        "explosionsschutz.ProtectionMeasure": "protection_measure",
    }
    wf_type = mapping.get(entity_type)
    if not wf_type:
        raise ValueError(f"Unbekannter Entity-Typ: {entity_type}")
    return wf_type


def _notify_rejection(
    request: ApprovalRequest,
    decision: ApprovalDecision,
) -> None:
    """Create notification for rejection."""
    try:
        from notifications.services import create_notification
        from notifications.models import Notification

        create_notification(
            tenant_id=request.tenant_id,
            category=Notification.Category.APPROVAL_REQUIRED,
            title=f"Freigabe abgelehnt: {request.entity_type}",
            message=(
                f"Stufe: {decision.step.name}\n"
                f"Grund: {decision.comment or 'Kein Kommentar'}"
            ),
            severity=Notification.Severity.WARNING,
            recipient_id=(
                request.requested_by.id
                if request.requested_by else None
            ),
            entity_type=request.entity_type,
            entity_id=request.entity_id,
        )
    except Exception:
        logger.exception("Failed to send rejection notification")


def _on_fully_approved(request: ApprovalRequest) -> None:
    """
    Callback when all approval steps are complete.

    Updates the entity status to 'approved'.
    """
    try:
        if request.entity_type == "explosionsschutz.ExplosionConcept":
            from explosionsschutz.models import ExplosionConcept
            ExplosionConcept.objects.filter(
                id=request.entity_id,
                tenant_id=request.tenant_id,
            ).update(status="approved")

        elif request.entity_type == "risk.Assessment":
            from risk.models import Assessment
            Assessment.objects.filter(
                id=request.entity_id,
                tenant_id=request.tenant_id,
            ).update(status="approved")

        logger.info(
            "Entity approved: %s %s",
            request.entity_type, request.entity_id,
        )
    except Exception:
        logger.exception(
            "Failed to update entity status after approval"
        )
