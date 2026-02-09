"""Celery tasks for notification processing."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="notifications.tasks.check_inspection_deadlines")
def check_inspection_deadlines() -> dict:
    """
    Daily task: scan all equipment for upcoming/overdue inspections
    and create notifications.
    """
    from notifications.services import scan_inspection_deadlines

    stats = scan_inspection_deadlines()
    logger.info("Inspection deadline check: %s", stats)
    return stats
