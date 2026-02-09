"""Notification service — creation, delivery, deadline scanning."""

import logging
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from django.db.models import Q
from django.utils import timezone

from notifications.models import Notification

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Notification CRUD
# ------------------------------------------------------------------

def create_notification(
    tenant_id: UUID,
    category: str,
    title: str,
    message: str = "",
    severity: str = Notification.Severity.INFO,
    recipient_id: Optional[UUID] = None,
    entity_type: str = "",
    entity_id: Optional[UUID] = None,
    action_url: str = "",
) -> Notification:
    """Create and persist a notification."""
    return Notification.objects.create(
        tenant_id=tenant_id,
        recipient_id=recipient_id,
        category=category,
        severity=severity,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
        action_url=action_url,
    )


def get_unread(
    tenant_id: UUID,
    user_id: Optional[UUID] = None,
    limit: int = 20,
) -> list[Notification]:
    """Return unread notifications for a tenant (optionally per user)."""
    qs = Notification.objects.filter(
        tenant_id=tenant_id,
        is_read=False,
    )
    if user_id:
        qs = qs.filter(
            Q(recipient_id=user_id) | Q(recipient_id__isnull=True)
        )
    return list(qs[:limit])


def get_unread_count(
    tenant_id: UUID,
    user_id: Optional[UUID] = None,
) -> int:
    """Return count of unread notifications."""
    qs = Notification.objects.filter(
        tenant_id=tenant_id,
        is_read=False,
    )
    if user_id:
        qs = qs.filter(
            Q(recipient_id=user_id) | Q(recipient_id__isnull=True)
        )
    return qs.count()


def mark_all_read(
    tenant_id: UUID,
    user_id: Optional[UUID] = None,
) -> int:
    """Mark all unread notifications as read. Returns count."""
    qs = Notification.objects.filter(
        tenant_id=tenant_id,
        is_read=False,
    )
    if user_id:
        qs = qs.filter(
            Q(recipient_id=user_id) | Q(recipient_id__isnull=True)
        )
    return qs.update(is_read=True, read_at=timezone.now())


# ------------------------------------------------------------------
# Deadline Scanner
# ------------------------------------------------------------------

DEFAULT_THRESHOLDS = [30, 7, 3, 1, 0]  # days before due


def scan_inspection_deadlines(
    threshold_days: list[int] | None = None,
) -> dict:
    """
    Scan all tenants for upcoming/overdue equipment inspections.

    Creates notifications for equipment whose next_inspection_date
    falls within one of the threshold windows. Skips if a matching
    notification already exists for the same entity + category +
    date window.

    Returns summary dict with counts per severity.
    """
    from explosionsschutz.models import Equipment

    thresholds = threshold_days or DEFAULT_THRESHOLDS
    today = date.today()
    stats = {"created": 0, "skipped": 0, "overdue": 0}

    equipment_qs = Equipment.objects.filter(
        next_inspection_date__isnull=False,
    ).select_related("equipment_type")

    for eq in equipment_qs.iterator(chunk_size=200):
        days_until = (eq.next_inspection_date - today).days

        # Determine which threshold bucket this falls into
        matched_threshold = None
        for t in sorted(thresholds):
            if days_until <= t:
                matched_threshold = t
                break

        if matched_threshold is None:
            stats["skipped"] += 1
            continue

        # Determine severity + category
        if days_until < 0:
            severity = Notification.Severity.CRITICAL
            category = Notification.Category.INSPECTION_OVERDUE
            stats["overdue"] += 1
        elif days_until <= 3:
            severity = Notification.Severity.CRITICAL
            category = Notification.Category.INSPECTION_DUE
        elif days_until <= 7:
            severity = Notification.Severity.WARNING
            category = Notification.Category.INSPECTION_DUE
        else:
            severity = Notification.Severity.INFO
            category = Notification.Category.INSPECTION_DUE

        # Dedup: skip if notification already exists for this
        # equipment + category in the same threshold window
        window_start = today - timedelta(days=1)
        already_exists = Notification.objects.filter(
            tenant_id=eq.tenant_id,
            entity_type="explosionsschutz.Equipment",
            entity_id=eq.id,
            category=category,
            created_at__date__gte=window_start,
        ).exists()

        if already_exists:
            stats["skipped"] += 1
            continue

        # Build notification
        if days_until < 0:
            title = (
                f"Prüfung überfällig: {eq.serial_number} "
                f"(seit {abs(days_until)} Tagen)"
            )
        elif days_until == 0:
            title = f"Prüfung heute fällig: {eq.serial_number}"
        else:
            title = (
                f"Prüfung in {days_until} Tagen: "
                f"{eq.serial_number}"
            )

        msg = (
            f"Betriebsmittel: {eq.serial_number}\n"
            f"Typ: {eq.equipment_type.name if eq.equipment_type else '–'}\n"
            f"Fällig am: {eq.next_inspection_date.isoformat()}"
        )

        create_notification(
            tenant_id=eq.tenant_id,
            category=category,
            title=title,
            message=msg,
            severity=severity,
            entity_type="explosionsschutz.Equipment",
            entity_id=eq.id,
            action_url=f"/ex/equipment/{eq.id}/",
        )
        stats["created"] += 1

    logger.info(
        "Inspection deadline scan complete: %s", stats
    )
    return stats
