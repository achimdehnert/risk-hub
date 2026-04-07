# src/global_sds/services/supersession_service.py
"""
SdsSupersessionService — Supersession-Kette + Notifications (ADR-012 §6.2).

Setzt alte Revision auf SUPERSEDED, erstellt Outbox-Events,
und flaggt GBU/Ex-Schutz-Dokumente bei SAFETY_CRITICAL.
"""

import logging
from datetime import date, timedelta

from django.conf import settings

from global_sds.models import (
    GlobalSdsRevision,
    ImpactLevel,
    SdsRevisionDiffRecord,
)
from global_sds.sds_usage import SdsUsage, SdsUsageStatus

logger = logging.getLogger(__name__)

REVIEW_DEADLINE_DAYS = getattr(
    settings,
    "SDS_REVIEW_DEADLINE_DAYS",
    28,
)


class SdsSupersessionService:
    """
    Führt Supersession durch:
    1. Alte Revision → SUPERSEDED
    2. Betroffene SdsUsages updaten
    3. GBU/Ex-Schutz flaggen bei SAFETY_CRITICAL
    4. Outbox-Events emittieren
    """

    def supersede(
        self,
        old_revision: GlobalSdsRevision,
        new_revision: GlobalSdsRevision,
        diff_record: SdsRevisionDiffRecord,
    ) -> int:
        """
        Supersession durchführen.

        Returns: Anzahl betroffener SdsUsages.
        """
        # 1. Alte Revision → SUPERSEDED
        old_revision.superseded_by = new_revision
        old_revision.status = GlobalSdsRevision.Status.SUPERSEDED
        old_revision.save(
            update_fields=["superseded_by", "status", "updated_at"],
        )

        # 2. Neue Revision → VERIFIED
        new_revision.status = GlobalSdsRevision.Status.VERIFIED
        new_revision.save(update_fields=["status", "updated_at"])

        # 3. Betroffene Tenants updaten
        impact = diff_record.overall_impact
        usages = SdsUsage.objects.filter(
            sds_revision=old_revision,
            status=SdsUsageStatus.ACTIVE,
        )
        affected = 0

        for usage in usages:
            usage.pending_update_revision = new_revision
            usage.pending_update_impact = impact

            if impact == ImpactLevel.SAFETY_CRITICAL:
                usage.status = SdsUsageStatus.REVIEW_REQUIRED
                usage.review_deadline = date.today() + timedelta(days=REVIEW_DEADLINE_DAYS)
            elif impact == ImpactLevel.REGULATORY:
                usage.status = SdsUsageStatus.UPDATE_AVAILABLE

            usage.save(
                update_fields=[
                    "pending_update_revision",
                    "pending_update_impact",
                    "status",
                    "review_deadline",
                    "updated_at",
                ]
            )
            affected += 1

            # 4. Outbox-Event
            self._emit_supersession_event(
                usage,
                old_revision,
                new_revision,
                diff_record,
                impact,
            )

        # 5. GBU/Ex-Schutz flaggen
        if impact == ImpactLevel.SAFETY_CRITICAL:
            self._flag_downstream(old_revision, diff_record)

        logger.info(
            "Superseded revision %s → %s, %d usages affected (impact=%s)",
            old_revision.pk,
            new_revision.pk,
            affected,
            impact,
        )
        return affected

    def _emit_supersession_event(
        self,
        usage: SdsUsage,
        old_revision: GlobalSdsRevision,
        new_revision: GlobalSdsRevision,
        diff_record: SdsRevisionDiffRecord,
        impact: str,
    ) -> None:
        """Outbox-Event emittieren (ADR-012 §6.5)."""
        try:
            from outbox.services import emit_audit_event

            emit_audit_event(
                tenant_id=str(usage.tenant_id),
                event_type="sds.revision_superseded",
                entity_type="SdsUsage",
                entity_id=str(usage.pk),
                payload={
                    "old_revision_id": str(old_revision.pk),
                    "new_revision_id": str(new_revision.pk),
                    "diff_record_id": str(diff_record.pk),
                    "impact_level": impact,
                    "added_h_codes": diff_record.added_h_codes,
                    "removed_h_codes": diff_record.removed_h_codes,
                    "requires_gbu_review": (impact == ImpactLevel.SAFETY_CRITICAL),
                    "requires_ex_review": (impact == ImpactLevel.SAFETY_CRITICAL),
                    "review_deadline": (
                        str(usage.review_deadline) if usage.review_deadline else None
                    ),
                },
            )
        except ImportError:
            logger.warning(
                "outbox.services not available, skipping audit event",
            )

    def _flag_downstream(
        self,
        old_revision: GlobalSdsRevision,
        diff_record: SdsRevisionDiffRecord,
    ) -> None:
        """GBU + Ex-Schutz bei SAFETY_CRITICAL flaggen."""
        reason = (
            f"SDS-Update: {diff_record.overall_impact}. Neue H-Sätze: {diff_record.added_h_codes}"
        )

        # GBU flaggen (falls Modul vorhanden)
        try:
            from gbu.models import HazardAssessment

            flagged = HazardAssessment.objects.filter(
                sds_usage__sds_revision=old_revision,
                status__in=["APPROVED", "ACTIVE"],
            ).update(
                review_required=True,
                review_reason=reason,
            )
            if flagged:
                logger.info(
                    "Flagged %d GBU assessments",
                    flagged,
                )
        except (ImportError, Exception) as exc:
            logger.debug(
                "GBU flagging skipped: %s",
                exc,
            )

        # Ex-Schutz flaggen (falls Modul vorhanden)
        try:
            from explosionsschutz.models import ExplosionConcept

            flagged = ExplosionConcept.objects.filter(
                substances__revisions=old_revision,
                status="APPROVED",
            ).update(
                review_required=True,
                review_reason=reason,
            )
            if flagged:
                logger.info(
                    "Flagged %d Ex-Schutz concepts",
                    flagged,
                )
        except (ImportError, Exception) as exc:
            logger.debug(
                "Ex-Schutz flagging skipped: %s",
                exc,
            )
