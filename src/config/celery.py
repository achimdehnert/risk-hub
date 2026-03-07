"""Celery configuration for Risk-Hub."""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("riskhub")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Beat schedule — periodic tasks
app.conf.beat_schedule = {
    "check-inspection-deadlines": {
        "task": "notifications.tasks.check_inspection_deadlines",
        "schedule": crontab(hour=6, minute=0),  # Daily at 06:00
    },
    "process-outbox": {
        "task": "outbox.tasks.process_outbox",
        "schedule": 30.0,  # Every 30 seconds
    },
    "check-gbu-review-deadlines": {
        "task": "gbu.tasks.check_review_deadlines",
        "schedule": crontab(hour=7, minute=0),  # Daily at 07:00
    },
    "cleanup-old-export-jobs": {
        "task": "reporting.cleanup_old_export_jobs",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Weekly Sunday 03:00
    },
}
app.conf.timezone = "Europe/Berlin"
