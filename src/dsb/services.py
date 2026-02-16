"""DSB KPI aggregation service (ADR-041 Phase 0)."""

import logging
from dataclasses import dataclass
from uuid import UUID

from django.db.models import Q

logger = logging.getLogger(__name__)


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
