"""
GBU-Engine Service Layer.

Phase 2A: Command DTOs + Service-Stubs mit Audit-Events
Phase 2B: EMKG-Risikobewertung (calculate_risk_score), approve_activity, set_risk_score
"""

import datetime
import logging
from dataclasses import dataclass
from uuid import UUID

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CreateActivityCmd:
    """Command DTO für neue GBU-Tätigkeit."""

    site_id: UUID
    sds_revision_id: UUID
    activity_description: str
    activity_frequency: str
    duration_minutes: int
    quantity_class: str
    substitution_checked: bool = False
    substitution_notes: str = ""


@dataclass(frozen=True)
class ApproveActivityCmd:
    """Command DTO für GBU-Freigabe."""

    activity_id: UUID
    next_review_date: datetime.date


def derive_hazard_categories(sds_revision_id: UUID) -> list:
    """
    H-Codes aus SdsRevision → Gefährdungskategorien nach TRGS 400.

    SdsRevision.hazard_statements ist ein ManyToManyField auf HazardStatementRef.
    HazardStatementRef.code enthält den H-Code (z.B. 'H220').
    Returns: list[HazardCategoryRef]
    """
    from gbu.models.reference import HazardCategoryRef
    from substances.models import SdsRevision

    revision = SdsRevision.objects.prefetch_related("hazard_statements").get(id=sds_revision_id)

    h_codes = list(revision.hazard_statements.values_list("code", flat=True))
    if not h_codes:
        return []

    return list(
        HazardCategoryRef.objects.filter(
            h_code_mappings__h_code__in=h_codes,
        )
        .distinct()
        .order_by("category_type", "sort_order")
    )


def propose_measures(activity_id: UUID) -> list:
    """
    TOPS-Maßnahmenvorschläge für eine GBU-Tätigkeit.
    Returns: list[MeasureTemplate]
    """
    from gbu.models.activity import HazardAssessmentActivity
    from gbu.models.reference import MeasureTemplate

    activity = HazardAssessmentActivity.objects.prefetch_related("derived_hazard_categories").get(
        id=activity_id
    )

    category_ids = list(activity.derived_hazard_categories.values_list("id", flat=True))
    if not category_ids:
        return []

    return list(
        MeasureTemplate.objects.filter(
            category_id__in=category_ids,
        ).order_by("tops_type", "sort_order")
    )


@transaction.atomic
def create_activity(
    cmd: CreateActivityCmd,
    tenant_id: UUID,
    user_id: UUID | None = None,
):
    """
    Neue GBU-Tätigkeit anlegen.

    Audit-Event ist Pflicht — GBU ist Rechtsdokument (GefStoffV §6).
    """
    from common.context import emit_audit_event
    from gbu.models.activity import ActivityStatus, HazardAssessmentActivity

    activity = HazardAssessmentActivity.objects.create(
        tenant_id=tenant_id,
        site_id=cmd.site_id,
        sds_revision_id=cmd.sds_revision_id,
        activity_description=cmd.activity_description.strip(),
        activity_frequency=cmd.activity_frequency,
        duration_minutes=cmd.duration_minutes,
        quantity_class=cmd.quantity_class,
        substitution_checked=cmd.substitution_checked,
        substitution_notes=cmd.substitution_notes,
        status=ActivityStatus.DRAFT,
        created_by=user_id,
    )

    emit_audit_event(
        tenant_id=tenant_id,
        category="compliance",
        action="created",
        entity_type="gbu.HazardAssessmentActivity",
        entity_id=activity.id,
        payload={
            "site_id": str(cmd.site_id),
            "sds_revision_id": str(cmd.sds_revision_id),
            "status": ActivityStatus.DRAFT,
        },
        user_id=user_id,
    )

    logger.info("[GBUEngine] Tätigkeit erstellt: %s (tenant=%s)", activity.id, tenant_id)
    return activity


def calculate_risk_score(
    quantity_class: str,
    activity_frequency: str,
    has_cmr: bool = False,
) -> str:
    """
    EMKG-Risikoscore aus Mengenkategorie + Frequenz + CMR-Flag.

    Liest aus ExposureRiskMatrix (admin-pflegbar).
    Fallback: 'high' wenn kein Eintrag gefunden (fail-safe für Compliance).

    Returns: RiskScore-Wert (str)
    """
    from gbu.models.reference import ExposureRiskMatrix

    entry = ExposureRiskMatrix.objects.filter(
        quantity_class=quantity_class,
        activity_frequency=activity_frequency,
        has_cmr=has_cmr,
    ).first()

    if entry is None:
        logger.warning(
            "[GBUEngine] Kein Risikomatrix-Eintrag für %s/%s/cmr=%s — Fallback: high",
            quantity_class,
            activity_frequency,
            has_cmr,
        )
        return "high"

    return entry.risk_score


@transaction.atomic
def approve_activity(
    cmd: "ApproveActivityCmd",
    tenant_id: UUID,
    user_id: UUID,
    approved_by_name: str = "",
) -> "HazardAssessmentActivity":  # noqa: F821
    """
    GBU-Tätigkeit freigeben.

    Setzt Status → APPROVED, schreibt Freigeber-Snapshot (UUID + Name),
    emittiert Audit-Event. Audit-Event ist Pflicht (GefStoffV §6).
    Nur DRAFT oder REVIEW darf freigegeben werden.
    """
    from common.context import emit_audit_event
    from gbu.models.activity import ActivityStatus, HazardAssessmentActivity

    activity = HazardAssessmentActivity.objects.select_for_update().get(
        id=cmd.activity_id,
        tenant_id=tenant_id,
    )

    if activity.status not in (ActivityStatus.DRAFT, ActivityStatus.REVIEW):
        raise ValueError(
            f"Status '{activity.status}' kann nicht freigegeben werden (nur draft/review zulässig)"
        )

    activity.status = ActivityStatus.APPROVED
    activity.approved_by_id = user_id
    activity.approved_by_name = approved_by_name
    activity.approved_at = timezone.now()
    activity.next_review_date = cmd.next_review_date
    activity.save(
        update_fields=[
            "status",
            "approved_by_id",
            "approved_by_name",
            "approved_at",
            "next_review_date",
            "updated_at",
        ]
    )

    emit_audit_event(
        tenant_id=tenant_id,
        category="compliance",
        action="approved",
        entity_type="gbu.HazardAssessmentActivity",
        entity_id=activity.id,
        payload={
            "approved_by_id": str(user_id),
            "approved_by_name": approved_by_name,
            "next_review_date": str(cmd.next_review_date),
        },
        user_id=user_id,
    )

    logger.info(
        "[GBUEngine] Tätigkeit freigegeben: %s (tenant=%s, by=%s)",
        activity.id,
        tenant_id,
        user_id,
    )
    return activity


@transaction.atomic
def set_risk_score(
    activity_id: UUID,
    tenant_id: UUID,
) -> "HazardAssessmentActivity":  # noqa: F821
    """
    EMKG-Risikoscore für eine Tätigkeit berechnen und speichern.

    CMR-Flag wird aus derived_hazard_categories ermittelt.
    """
    from gbu.models.activity import HazardAssessmentActivity
    from gbu.models.reference import HazardCategoryType

    activity = (
        HazardAssessmentActivity.objects.prefetch_related("derived_hazard_categories")
        .select_for_update()
        .get(id=activity_id, tenant_id=tenant_id)
    )

    has_cmr = activity.derived_hazard_categories.filter(
        category_type=HazardCategoryType.CMR
    ).exists()

    score = calculate_risk_score(
        quantity_class=activity.quantity_class,
        activity_frequency=activity.activity_frequency,
        has_cmr=has_cmr,
    )

    activity.risk_score = score
    activity.save(update_fields=["risk_score", "updated_at"])

    logger.info(
        "[GBUEngine] Risikoscore gesetzt: %s → %s (cmr=%s)",
        activity.id,
        score,
        has_cmr,
    )
    return activity
