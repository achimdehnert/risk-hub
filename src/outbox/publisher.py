"""Outbox publisher worker."""

import os
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.db import transaction
from django.utils import timezone

from outbox.models import OutboxMessage

POLL_SECONDS = 2


def publish(msg: OutboxMessage) -> None:
    """Publish message (MVP: just print)."""
    print(f"[OUTBOX] topic={msg.topic} tenant={msg.tenant_id} payload={msg.payload}")


def run_forever():
    """Poll outbox and publish messages."""
    print("[OUTBOX] Publisher started")
    while True:
        with transaction.atomic():
            qs = (
                OutboxMessage.objects
                .select_for_update(skip_locked=True)
                .filter(published_at__isnull=True)
                .order_by("created_at")[:50]
            )
            msgs = list(qs)
            for m in msgs:
                publish(m)
                m.published_at = timezone.now()
                m.save(update_fields=["published_at"])
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run_forever()
