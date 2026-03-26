# src/global_sds/services/usage_service.py
"""
SdsUsageService — Tenant-Aktionen (ADR-012 §6.4).

adopt_update(): Neue Revision übernehmen.
defer_update(): Zurückstellen mit Pflichtbegründung.
"""

import logging
from datetime import date

from django.contrib.auth import get_user_model

from global_sds.sds_usage import SdsUsage, SdsUsageStatus

logger = logging.getLogger(__name__)

User = get_user_model()


class SdsUsageService:
    """Tenant-seitige Aktionen auf SdsUsage."""

    def adopt_update(
        self,
        usage: SdsUsage,
        user: "User",
    ) -> SdsUsage:
        """
        Neue Revision übernehmen.

        Erstellt neuen SdsUsage mit pending_update_revision
        und setzt alten auf SUPERSEDED.
        """
        if not usage.pending_update_revision:
            raise ValueError(
                "Kein pending Update vorhanden",
            )

        new_revision = usage.pending_update_revision

        # Neuen SdsUsage erstellen
        new_usage = SdsUsage.objects.create(
            tenant_id=usage.tenant_id,
            sds_revision=new_revision,
            status=SdsUsageStatus.ACTIVE,
            approved_by=user,
            approval_date=date.today(),
        )

        # Alten auf SUPERSEDED setzen
        usage.status = SdsUsageStatus.SUPERSEDED
        usage.save(update_fields=["status", "updated_at"])

        # Outbox-Event
        self._emit_adopt_event(usage, new_usage, user)

        logger.info(
            "Adopted update: Usage %s → %s (by %s)",
            usage.pk, new_usage.pk, user,
        )
        return new_usage

    def defer_update(
        self,
        usage: SdsUsage,
        user: "User",
        reason: str,
        deferred_until: date | None = None,
    ) -> SdsUsage:
        """
        Update zurückstellen mit Pflichtbegründung.

        GefStoffV §7: reason darf NICHT leer sein.
        """
        if not reason or not reason.strip():
            raise ValueError(
                "Pflichtbegründung fehlt "
                "(GefStoffV §7 Compliance)",
            )

        usage.update_deferred_reason = reason.strip()
        usage.update_deferred_until = deferred_until
        usage.update_deferred_by = user
        usage.save(update_fields=[
            "update_deferred_reason",
            "update_deferred_until",
            "update_deferred_by",
            "updated_at",
        ])

        # Outbox-Event
        self._emit_defer_event(usage, user, reason)

        logger.info(
            "Deferred update: Usage %s (by %s, until %s)",
            usage.pk, user, deferred_until,
        )
        return usage

    def _emit_adopt_event(
        self,
        old_usage: SdsUsage,
        new_usage: SdsUsage,
        user: "User",
    ) -> None:
        """Outbox-Event für Übernahme."""
        try:
            from outbox.services import emit_audit_event

            emit_audit_event(
                tenant_id=str(new_usage.tenant_id),
                event_type="sds.usage_update_adopted",
                entity_type="SdsUsage",
                entity_id=str(new_usage.pk),
                payload={
                    "old_usage_id": str(old_usage.pk),
                    "new_usage_id": str(new_usage.pk),
                    "adopted_by_user_id": str(user.pk),
                },
            )
        except ImportError:
            logger.debug("outbox not available")

    def _emit_defer_event(
        self,
        usage: SdsUsage,
        user: "User",
        reason: str,
    ) -> None:
        """Outbox-Event für Zurückstellung."""
        try:
            from outbox.services import emit_audit_event

            emit_audit_event(
                tenant_id=str(usage.tenant_id),
                event_type="sds.usage_update_deferred",
                entity_type="SdsUsage",
                entity_id=str(usage.pk),
                payload={
                    "deferred_by_user_id": str(user.pk),
                    "reason": reason,
                    "deferred_until": (
                        str(usage.update_deferred_until)
                        if usage.update_deferred_until
                        else None
                    ),
                    "impact_level": (
                        usage.pending_update_impact
                    ),
                },
            )
        except ImportError:
            logger.debug("outbox not available")
