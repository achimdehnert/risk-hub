"""DSB service layer (ADR-041).

CRUD operations + KPI aggregation. Views must not call .save() / .delete()
directly — always go through this module.
"""

import contextlib
import logging
from dataclasses import dataclass
from uuid import UUID

from django.db.models import Q

from common.services import delete_object, save_form  # noqa: F401

logger = logging.getLogger(__name__)


def create_dsb_document(
    tenant_id: UUID,
    mandate,
    ref_type: str,
    ref_id: str | None,
    title: str,
    description: str,
    uploaded_file,
    mime_type: str = "",
    uploaded_by_id: int | None = None,
    document_date: str | None = None,
):
    """Create a DsbDocument with file upload (ADR-041)."""
    from dsb.models.document import DsbDocument

    doc = DsbDocument(
        tenant_id=tenant_id,
        mandate=mandate,
        ref_type=ref_type,
        ref_id=ref_id,
        title=title,
        description=description,
        original_filename=uploaded_file.name,
        file_size=uploaded_file.size,
        mime_type=mime_type,
        uploaded_by_id=uploaded_by_id,
    )
    if document_date:
        from datetime import datetime

        with contextlib.suppress(ValueError):
            doc.document_date = datetime.strptime(
                document_date,
                "%Y-%m-%d",
            ).date()
    doc.file = uploaded_file
    doc.save()
    return doc


@dataclass(frozen=True)
class DsbKPI:
    """Aggregated DSB KPIs for a tenant."""

    # Mandate
    mandates_active: int = 0
    mandates_total: int = 0

    # VVT (Art. 30)
    vvt_total: int = 0
    vvt_high_risk: int = 0
    vvt_dsfa_required: int = 0
    third_country_transfers: int = 0

    # TOM (Art. 32)
    tom_tech_total: int = 0
    tom_tech_implemented: int = 0
    tom_tech_planned: int = 0
    tom_org_total: int = 0
    tom_org_implemented: int = 0
    tom_org_planned: int = 0

    # AVV (Art. 28)
    dpa_total: int = 0
    dpa_active: int = 0
    dpa_expired: int = 0

    # Audits
    audits_total: int = 0
    audits_planned: int = 0
    audits_completed: int = 0
    findings_open: int = 0
    findings_critical: int = 0

    # Deletion (Art. 17)
    deletions_total: int = 0
    deletions_pending: int = 0

    # Breach (Art. 33)
    breaches_total: int = 0
    breaches_open: int = 0
    breaches_overdue: int = 0


def get_cmr_dsfa_hints(tenant_id: UUID) -> list[dict]:
    """
    Gibt alle CMR-Stoffe zurück, die im Standort-Inventar des Tenants vorhanden sind,
    aber für die keine ProcessingActivity mit dsfa_required=True existiert.

    Hintergrund: Gesundheitsdaten von Beschäftigten (Exposition gegenüber CMR-Stoffen,
    arbeitsmedizinische Vorsorge) sind besondere Datenkategorien nach Art. 9 DSGVO
    und erfordern in der Regel eine DSFA (Art. 35 DSGVO).

    Returns: Liste von dicts mit {substance_id, substance_name, site_id}
    """
    from dsb.models.vvt import ProcessingActivity
    from substances.models import SiteInventoryItem

    cmr_items = (
        SiteInventoryItem.objects.filter(
            tenant_id=tenant_id,
            substance__is_cmr=True,
            substance__status="active",
        )
        .select_related("substance", "site")
        .distinct()
    )

    dsfa_exists = ProcessingActivity.objects.filter(
        tenant_id=tenant_id,
        dsfa_required=True,
    ).exists()

    hints = []
    for item in cmr_items:
        hints.append(
            {
                "substance_id": str(item.substance_id),
                "substance_name": item.substance.name,
                "site_id": str(item.site_id) if item.site_id else None,
                "dsfa_covered": dsfa_exists,
                "hint": (
                    "CMR-Stoff im Inventar — DSFA nach Art. 35 DSGVO prüfen"
                    if not dsfa_exists
                    else "CMR-Stoff im Inventar — DSFA vorhanden"
                ),
            }
        )
    return hints


def get_dsb_kpis(tenant_id: UUID) -> DsbKPI:
    """Aggregate all DSB KPIs for a tenant."""
    from dsb.models import (
        Breach,
        DataProcessingAgreement,
        DeletionLog,
        Mandate,
        OrganizationalMeasure,
        PrivacyAudit,
        ProcessingActivity,
        TechnicalMeasure,
    )
    from dsb.models.audit import AuditFinding
    from dsb.models.choices import MeasureStatus, SeverityLevel

    tf = Q(tenant_id=tenant_id)

    # --- Mandate ---
    mandates = Mandate.objects.filter(tf)
    mandates_active = mandates.filter(status="active").count()

    # --- VVT (Art. 30) ---
    vvt = ProcessingActivity.objects.filter(tf)
    vvt_total = vvt.count()
    vvt_high_risk = vvt.filter(
        risk_level__in=["high", "very_high"],
    ).count()
    vvt_dsfa = vvt.filter(dsfa_required=True).count()

    from dsb.models import ThirdCountryTransfer

    transfers = ThirdCountryTransfer.objects.filter(tf).count()

    # --- TOM (Art. 32) ---
    tech = TechnicalMeasure.objects.filter(tf)
    org = OrganizationalMeasure.objects.filter(tf)

    # --- AVV (Art. 28) ---
    dpa = DataProcessingAgreement.objects.filter(tf)
    dpa_active = dpa.filter(status="active").count()
    dpa_expired = dpa.filter(status="expired").count()

    # --- Audits ---
    audits = PrivacyAudit.objects.filter(tf)
    findings = AuditFinding.objects.filter(tf)

    # --- Deletion (Art. 17) ---
    deletions = DeletionLog.objects.filter(tf)
    deletions_pending = deletions.filter(executed_at__isnull=True).count()

    # --- Breach (Art. 33) ---
    breaches = Breach.objects.filter(tf)
    breaches_open = breaches.filter(
        reported_to_authority_at__isnull=True,
    ).count()
    breaches_overdue = sum(1 for b in breaches if b.is_overdue)

    return DsbKPI(
        mandates_active=mandates_active,
        mandates_total=mandates.count(),
        vvt_total=vvt_total,
        vvt_high_risk=vvt_high_risk,
        vvt_dsfa_required=vvt_dsfa,
        third_country_transfers=transfers,
        tom_tech_total=tech.count(),
        tom_tech_implemented=tech.filter(
            status=MeasureStatus.IMPLEMENTED,
        ).count(),
        tom_tech_planned=tech.filter(
            status=MeasureStatus.PLANNED,
        ).count(),
        tom_org_total=org.count(),
        tom_org_implemented=org.filter(
            status=MeasureStatus.IMPLEMENTED,
        ).count(),
        tom_org_planned=org.filter(
            status=MeasureStatus.PLANNED,
        ).count(),
        dpa_total=dpa.count(),
        dpa_active=dpa_active,
        dpa_expired=dpa_expired,
        audits_total=audits.count(),
        audits_planned=audits.filter(status="planned").count(),
        audits_completed=audits.filter(status="completed").count(),
        findings_open=findings.filter(status="open").count(),
        findings_critical=findings.filter(
            severity=SeverityLevel.CRITICAL,
            status="open",
        ).count(),
        deletions_total=deletions.count(),
        deletions_pending=deletions_pending,
        breaches_total=breaches.count(),
        breaches_open=breaches_open,
        breaches_overdue=breaches_overdue,
    )


# ---------------------------------------------------------------------------
# Query helpers (ADR-041)
# ---------------------------------------------------------------------------


def get_open_breaches(tenant_id):
    """Return open Breaches (not closed) for a tenant, ordered by discovered_at."""
    from dsb.models import Breach

    return (
        Breach.objects.filter(tenant_id=tenant_id)
        .exclude(workflow_status__in=["closed", "authority_closed"])
        .select_related("mandate")
        .order_by("discovered_at")
    )


def get_open_deletion_requests(tenant_id):
    """Return pending DeletionRequests for a tenant."""
    from dsb.models.deletion_request import DeletionRequest

    return (
        DeletionRequest.objects.filter(tenant_id=tenant_id)
        .exclude(status__in=["completed", "rejected"])
        .select_related("mandate")
        .order_by("created_at")
    )


def get_processing_activities(tenant_id):
    """Return ProcessingActivities for a tenant."""
    from dsb.models import ProcessingActivity

    return ProcessingActivity.objects.filter(tenant_id=tenant_id)


def get_technical_measures(tenant_id):
    """Return TechnicalMeasures for a tenant."""
    from dsb.models import TechnicalMeasure

    return TechnicalMeasure.objects.filter(tenant_id=tenant_id)


def get_organizational_measures(tenant_id):
    """Return OrganizationalMeasures for a tenant."""
    from dsb.models import OrganizationalMeasure

    return OrganizationalMeasure.objects.filter(tenant_id=tenant_id)


def get_data_processing_agreements(tenant_id):
    """Return DataProcessingAgreements for a tenant."""
    from dsb.models import DataProcessingAgreement

    return DataProcessingAgreement.objects.filter(tenant_id=tenant_id)


def get_privacy_audits(tenant_id):
    """Return PrivacyAudits for a tenant."""
    from dsb.models import PrivacyAudit

    return PrivacyAudit.objects.filter(tenant_id=tenant_id)


def get_critical_audit_findings(tenant_id):
    """Return count of open critical AuditFindings for a tenant."""
    from dsb.models.audit import AuditFinding
    from dsb.models.choices import SeverityLevel

    return AuditFinding.objects.filter(
        tenant_id=tenant_id,
        severity=SeverityLevel.CRITICAL,
        status="open",
    ).count()


def get_deletion_logs(tenant_id):
    """Return DeletionLog entries for a tenant."""
    from dsb.models.deletion_log import DeletionLog

    return DeletionLog.objects.filter(tenant_id=tenant_id)


def get_active_mandates(tenant_id):
    """Return active Mandates for a tenant, or none() if no tenant."""
    from dsb.models import Mandate

    if tenant_id:
        return Mandate.objects.filter(tenant_id=tenant_id, status="active")
    return Mandate.objects.none()


def get_mandates(tenant_id):
    """Return all Mandates for a tenant ordered by name."""
    from dsb.models import Mandate

    return Mandate.objects.filter(tenant_id=tenant_id).order_by("name")


def get_dpa_documents(tenant_id, ref_id):
    """Return DsbDocuments for a DPA (ref_type='dpa')."""
    from dsb.models.document import DsbDocument

    return DsbDocument.objects.filter(tenant_id=tenant_id, ref_type="dpa", ref_id=ref_id)


def get_tenant_memberships(user):
    """Return Memberships for a user with organization prefetched."""
    from tenancy.models import Membership

    return (
        Membership.objects.filter(user=user)
        .select_related("organization")
        .order_by("created_at")
    )


def get_breaches(tenant_id):
    """Return all Breaches for a tenant."""
    from dsb.models import Breach

    return Breach.objects.filter(tenant_id=tenant_id)


def get_mandate_by_id(pk, tenant_id):
    """Return Mandate by PK + tenant, or None."""
    from dsb.models import Mandate

    return Mandate.objects.filter(pk=pk, tenant_id=tenant_id).first()
