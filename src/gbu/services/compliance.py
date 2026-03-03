"""
GBU Compliance-Service (Phase 2E).

Funktionen:
  list_due_reviews()       — Tätigkeiten mit fälligem Review (today + warning_days)
  list_overdue_reviews()   — Tätigkeiten mit überfälligem Review
  mark_outdated_activities() — Setzt status=OUTDATED für überfällige APPROVED-Einträge
  compliance_summary()     — Tenant-Übersicht für Dashboard
"""
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

_WARNING_DAYS = 30


@dataclass(frozen=True)
class ComplianceSummary:
    """Tenant-Compliance-Kennzahlen für das Dashboard."""

    total_approved: int
    due_soon: int
    overdue: int
    outdated: int
    draft_count: int

    @property
    def has_issues(self) -> bool:
        return self.overdue > 0 or self.outdated > 0


def list_due_reviews(
    tenant_id: UUID,
    warning_days: int = _WARNING_DAYS,
) -> list:
    """
    Tätigkeiten deren next_review_date innerhalb der nächsten `warning_days`
    Tage fällig ist (aber noch nicht überfällig).

    Returns: list[HazardAssessmentActivity]
    """
    from gbu.models.activity import ActivityStatus, HazardAssessmentActivity

    today = date.today()
    deadline = today + timedelta(days=warning_days)

    return list(
        HazardAssessmentActivity.objects
        .filter(
            tenant_id=tenant_id,
            status=ActivityStatus.APPROVED,
            next_review_date__gte=today,
            next_review_date__lte=deadline,
        )
        .select_related("site", "sds_revision", "sds_revision__substance")
        .order_by("next_review_date")
    )


def list_overdue_reviews(tenant_id: UUID) -> list:
    """
    Tätigkeiten mit next_review_date < today und status=APPROVED.

    Returns: list[HazardAssessmentActivity]
    """
    from gbu.models.activity import ActivityStatus, HazardAssessmentActivity

    return list(
        HazardAssessmentActivity.objects
        .filter(
            tenant_id=tenant_id,
            status=ActivityStatus.APPROVED,
            next_review_date__lt=date.today(),
        )
        .select_related("site", "sds_revision", "sds_revision__substance")
        .order_by("next_review_date")
    )


@transaction.atomic
def mark_outdated_activities(tenant_id: UUID) -> int:
    """
    Setzt status=OUTDATED für alle APPROVED-Tätigkeiten mit
    next_review_date < today und emittiert Audit-Events.

    Returns: Anzahl der aktualisierten Einträge
    """
    from common.context import emit_audit_event
    from gbu.models.activity import ActivityStatus, HazardAssessmentActivity

    overdue = list(
        HazardAssessmentActivity.objects
        .select_for_update(skip_locked=True)
        .filter(
            tenant_id=tenant_id,
            status=ActivityStatus.APPROVED,
            next_review_date__lt=date.today(),
        )
    )

    count = 0
    for activity in overdue:
        activity.status = ActivityStatus.OUTDATED
        activity.save(update_fields=["status", "updated_at"])

        emit_audit_event(
            tenant_id=tenant_id,
            category="compliance",
            action="outdated",
            entity_type="gbu.HazardAssessmentActivity",
            entity_id=activity.id,
            payload={
                "next_review_date": str(activity.next_review_date),
                "marked_outdated_at": timezone.now().isoformat(),
            },
            user_id=None,
        )
        count += 1

    if count:
        logger.info(
            "[GBU Compliance] %d T\u00e4tigkeiten als outdated markiert (tenant=%s)",
            count,
            tenant_id,
        )
    return count


def compliance_summary(tenant_id: UUID) -> ComplianceSummary:
    """
    Kompakte Compliance-Kennzahlen f\u00fcr den Dashboard-Header.
    """
    from gbu.models.activity import ActivityStatus, HazardAssessmentActivity

    qs = HazardAssessmentActivity.objects.filter(tenant_id=tenant_id)
    today = date.today()
    deadline = today + timedelta(days=_WARNING_DAYS)

    total_approved = qs.filter(status=ActivityStatus.APPROVED).count()
    overdue = qs.filter(
        status=ActivityStatus.APPROVED,
        next_review_date__lt=today,
    ).count()
    due_soon = qs.filter(
        status=ActivityStatus.APPROVED,
        next_review_date__gte=today,
        next_review_date__lte=deadline,
    ).count()
    outdated = qs.filter(status=ActivityStatus.OUTDATED).count()
    draft_count = qs.filter(status=ActivityStatus.DRAFT).count()

    return ComplianceSummary(
        total_approved=total_approved,
        due_soon=due_soon,
        overdue=overdue,
        outdated=outdated,
        draft_count=draft_count,
    )
