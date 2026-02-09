"""Dashboard KPI aggregation service."""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from django.db.models import Q

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ComplianceKPI:
    """Aggregated compliance KPIs for a tenant."""

    # Explosionsschutz
    areas_total: int = 0
    areas_with_hazard: int = 0
    concepts_total: int = 0
    concepts_draft: int = 0
    concepts_validated: int = 0
    concepts_approved: int = 0
    zones_total: int = 0
    equipment_total: int = 0
    inspections_overdue: int = 0
    inspections_due_7d: int = 0
    inspections_due_30d: int = 0
    measures_open: int = 0

    # Gefahrstoffe
    substances_total: int = 0
    sds_current: int = 0
    sds_outdated: int = 0
    site_inventory_items: int = 0

    # Risikobewertung
    assessments_total: int = 0
    assessments_open: int = 0
    actions_open: int = 0
    actions_overdue: int = 0

    # Notifications
    notifications_unread: int = 0
    notifications_critical: int = 0


@dataclass(frozen=True)
class RecentActivity:
    """A single recent activity entry."""

    icon: str = ""
    color: str = "gray"
    title: str = ""
    detail: str = ""
    timestamp: str = ""
    url: str = ""


def get_compliance_kpis(tenant_id: UUID) -> ComplianceKPI:
    """Aggregate all compliance KPIs for a tenant."""
    from actions.models import ActionItem
    from explosionsschutz.models import (
        Area,
        Equipment,
        ExplosionConcept,
        ProtectionMeasure,
        ZoneDefinition,
    )
    from notifications.models import Notification
    from substances.models import SdsRevision, Substance

    today = date.today()
    tf = Q(tenant_id=tenant_id)

    # --- Explosionsschutz ---
    areas = Area.objects.filter(tf)
    concepts = ExplosionConcept.objects.filter(tf)
    equipment = Equipment.objects.filter(tf)

    inspections_overdue = equipment.filter(
        next_inspection_date__lt=today,
    ).count()
    inspections_due_7d = equipment.filter(
        next_inspection_date__gte=today,
        next_inspection_date__lte=today + timedelta(days=7),
    ).count()
    inspections_due_30d = equipment.filter(
        next_inspection_date__gte=today,
        next_inspection_date__lte=today + timedelta(days=30),
    ).count()

    # --- Gefahrstoffe ---
    substances = Substance.objects.filter(tf)
    sds_qs = SdsRevision.objects.filter(tf)
    two_years_ago = today - timedelta(days=730)

    # --- Risikobewertung ---
    try:
        from risk.models import RiskAssessment
        assessments = RiskAssessment.objects.filter(tf)
        assessments_total = assessments.count()
        assessments_open = assessments.exclude(
            status="approved"
        ).count()
    except Exception:
        assessments_total = 0
        assessments_open = 0

    actions_qs = ActionItem.objects.filter(tf)

    # --- Notifications ---
    notifs = Notification.objects.filter(tf, is_read=False)

    return ComplianceKPI(
        areas_total=areas.count(),
        areas_with_hazard=areas.filter(
            has_explosion_hazard=True
        ).count(),
        concepts_total=concepts.count(),
        concepts_draft=concepts.filter(status="draft").count(),
        concepts_validated=concepts.filter(
            status="validated"
        ).count(),
        concepts_approved=concepts.filter(
            status="approved"
        ).count(),
        zones_total=ZoneDefinition.objects.filter(tf).count(),
        equipment_total=equipment.count(),
        inspections_overdue=inspections_overdue,
        inspections_due_7d=inspections_due_7d,
        inspections_due_30d=inspections_due_30d,
        measures_open=ProtectionMeasure.objects.filter(
            tf, status="open"
        ).count(),
        substances_total=substances.count(),
        sds_current=sds_qs.filter(
            revision_date__gte=two_years_ago
        ).values("substance_id").distinct().count(),
        sds_outdated=sds_qs.filter(
            revision_date__lt=two_years_ago
        ).values("substance_id").distinct().count(),
        site_inventory_items=0,  # TODO: SiteInventoryItem
        assessments_total=assessments_total,
        assessments_open=assessments_open,
        actions_open=actions_qs.exclude(
            status="done"
        ).count(),
        actions_overdue=actions_qs.filter(
            due_date__lt=today,
        ).exclude(status="done").count(),
        notifications_unread=notifs.count(),
        notifications_critical=notifs.filter(
            severity="critical"
        ).count(),
    )


def get_recent_activities(
    tenant_id: UUID,
    limit: int = 10,
) -> list[dict]:
    """Get recent audit events as activity feed."""
    from audit.models import AuditEvent

    events = AuditEvent.objects.filter(
        tenant_id=tenant_id,
    ).order_by("-created_at")[:limit]

    activities = []
    for ev in events:
        icon = _event_icon(ev.category)
        activities.append({
            "icon": icon[0],
            "color": icon[1],
            "title": f"{ev.category}.{ev.action}",
            "detail": str(ev.entity_type or ""),
            "timestamp": ev.created_at.strftime("%d.%m. %H:%M"),
            "url": "",
        })
    return activities


def _event_icon(category: str) -> tuple[str, str]:
    """Map audit category to (lucide-icon, tailwind-color)."""
    mapping = {
        "explosionsschutz": ("zap", "orange"),
        "risk": ("shield-alert", "red"),
        "substance": ("flask-conical", "purple"),
        "document": ("file-text", "blue"),
        "action": ("check-square", "green"),
        "inspection": ("clipboard-check", "teal"),
    }
    for key, val in mapping.items():
        if key in category.lower():
            return val
    return ("activity", "gray")
