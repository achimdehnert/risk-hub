"""
risk-hub Celery Configuration
=============================

Asynchrone Task-Verarbeitung für:
- Outbox Event Publishing
- Report Generation
- Document Processing
- Scheduled Jobs
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("risk_hub")

# Load config from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all apps
app.autodiscover_tasks()


# =============================================================================
# Celery Beat Schedule
# =============================================================================

app.conf.beat_schedule = {
    # Outbox Publisher (alle 10 Sekunden)
    "outbox-publisher": {
        "task": "apps.outbox.tasks.publish_pending_messages",
        "schedule": 10.0,
    },
    # Retention Cleanup (täglich 3:00)
    "retention-cleanup": {
        "task": "apps.documents.tasks.cleanup_expired_documents",
        "schedule": crontab(hour=3, minute=0),
    },
    # Report Job Cleanup (stündlich)
    "report-cleanup": {
        "task": "apps.reporting.tasks.cleanup_old_jobs",
        "schedule": crontab(minute=0),
    },
}


# =============================================================================
# Task Queues
# =============================================================================

app.conf.task_routes = {
    # Outbox: hohe Priorität
    "apps.outbox.tasks.*": {"queue": "outbox"},
    # Reports: separate Queue (kann lange dauern)
    "apps.reporting.tasks.*": {"queue": "reports"},
    # Default: alles andere
    "*": {"queue": "default"},
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing."""
    print(f"Request: {self.request!r}")
