"""Risk assessment services."""

from dataclasses import dataclass
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from common.context import emit_audit_event, emit_outbox_event, get_context
from permissions.authz import require_permission
from risk.models import Assessment, Hazard


@dataclass(frozen=True)
class CreateAssessmentCmd:
    """Command to create an assessment."""

    title: str
    description: str = ""
    category: str = "general"
    site_id: int | None = None


@dataclass(frozen=True)
class ApproveAssessmentCmd:
    """Command to approve an assessment."""

    assessment_id: UUID


def list_assessments(
    limit: int = 100,
    offset: int = 0,
) -> list[Assessment]:
    ctx = get_context()
    if ctx.tenant_id is None:
        raise ValueError("Tenant required")

    require_permission("risk.assessment.read")

    return list(
        Assessment.objects.filter(tenant_id=ctx.tenant_id).order_by("-created_at")[
            offset : offset + limit
        ]
    )


def get_assessment(assessment_id: UUID) -> Assessment:
    ctx = get_context()
    if ctx.tenant_id is None:
        raise ValueError("Tenant required")

    require_permission("risk.assessment.read")

    return Assessment.objects.get(
        id=assessment_id,
        tenant_id=ctx.tenant_id,
    )


@transaction.atomic
def create_assessment(cmd: CreateAssessmentCmd) -> Assessment:
    """Create a new risk assessment."""
    ctx = get_context()
    if ctx.tenant_id is None:
        raise ValueError("Tenant required")

    require_permission("risk.assessment.write")

    assessment = Assessment.objects.create(
        tenant_id=ctx.tenant_id,
        title=cmd.title.strip(),
        description=cmd.description,
        category=cmd.category,
        site_id=cmd.site_id,
        status="draft",
        created_by_id=ctx.user_id,
    )

    emit_audit_event(
        tenant_id=ctx.tenant_id,
        category="risk.assessment",
        action="created",
        entity_type="risk.Assessment",
        entity_id=assessment.id,
        payload={"title": assessment.title, "category": assessment.category},
    )

    emit_outbox_event(
        tenant_id=ctx.tenant_id,
        topic="risk.assessment.created",
        payload={
            "assessment_id": str(assessment.id),
            "title": assessment.title,
        },
    )

    return assessment


@transaction.atomic
def approve_assessment(cmd: ApproveAssessmentCmd) -> Assessment:
    """Approve a risk assessment."""
    ctx = get_context()
    if ctx.tenant_id is None:
        raise ValueError("Tenant required")

    require_permission("risk.assessment.approve")

    assessment = Assessment.objects.get(
        id=cmd.assessment_id,
        tenant_id=ctx.tenant_id,
    )

    if assessment.status not in ("draft", "in_review"):
        raise ValueError(f"Cannot approve assessment in status: {assessment.status}")

    assessment.status = "approved"
    assessment.approved_by_id = ctx.user_id
    assessment.approved_at = timezone.now()
    assessment.save(
        update_fields=[
            "status",
            "approved_by_id",
            "approved_at",
            "updated_at",
        ]
    )

    emit_audit_event(
        tenant_id=assessment.tenant_id,
        category="risk.assessment",
        action="approved",
        entity_type="risk.Assessment",
        entity_id=assessment.id,
        payload={"status": assessment.status},
    )

    emit_outbox_event(
        tenant_id=assessment.tenant_id,
        topic="risk.assessment.approved",
        payload={"assessment_id": str(assessment.id)},
    )

    return assessment


def list_hazards(
    assessment_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Hazard]:
    """List hazards, optionally filtered by assessment."""
    ctx = get_context()
    if ctx.tenant_id is None:
        raise ValueError("Tenant required")

    require_permission("risk.assessment.read")

    qs = Hazard.objects.filter(tenant_id=ctx.tenant_id).order_by("-created_at")
    if assessment_id is not None:
        qs = qs.filter(assessment_id=assessment_id)
    return list(qs[offset : offset + limit])


def get_hazard(hazard_id: UUID) -> Hazard:
    """Get a single hazard by ID."""
    ctx = get_context()
    if ctx.tenant_id is None:
        raise ValueError("Tenant required")

    require_permission("risk.assessment.read")

    return Hazard.objects.get(
        id=hazard_id,
        tenant_id=ctx.tenant_id,
    )


async def analyze_hazard_with_ai(hazard_description: str) -> str:
    """Analyze hazard using AI — powered by aifw."""
    from ai_analysis.llm_client import llm_complete

    system = (
        "Du bist ein Experte für Gefährdungsbeurteilungen und "
        "Arbeitssicherheit.\n"
        "Analysiere die beschriebene Gefährdung und gib "
        "Empfehlungen für Schutzmaßnahmen."
    )
    user = (
        "Analysiere folgende Gefährdung und schlage geeignete "
        "Schutzmaßnahmen vor:\n\n"
        f"{hazard_description}\n\n"
        "Bitte strukturiere deine Antwort wie folgt:\n"
        "1. Risikoeinschätzung\n"
        "2. Empfohlene Schutzmaßnahmen\n"
        "3. Priorität der Maßnahmen"
    )

    try:
        return await llm_complete(
            system=system,
            prompt=user,
            action_code="hazard_analysis",
        )
    except RuntimeError as exc:
        return f"Analyse fehlgeschlagen: {exc}"


# ---------------------------------------------------------------------------
# Query helpers (ADR-041)
# ---------------------------------------------------------------------------


def get_assessments(tenant_id):
    """Return Assessment queryset for a tenant."""
    from risk.models import Assessment

    return Assessment.objects.filter(tenant_id=tenant_id)


def get_hazards(tenant_id):
    """Return Hazard queryset for a tenant."""
    from risk.models import Hazard

    return Hazard.objects.filter(tenant_id=tenant_id)


def get_protective_measures(tenant_id):
    """Return ProtectiveMeasure queryset for a tenant."""
    from risk.models import ProtectiveMeasure

    return ProtectiveMeasure.objects.filter(tenant_id=tenant_id)


def get_substitution_checks(tenant_id):
    """Return SubstitutionCheck queryset for a tenant."""
    from risk.models import SubstitutionCheck

    return SubstitutionCheck.objects.filter(tenant_id=tenant_id)


def get_active_products(tenant_id):
    """Return active Products for a tenant ordered by trade_name."""
    from substances.models import Product

    return Product.objects.filter(tenant_id=tenant_id, status="active").order_by("trade_name")
