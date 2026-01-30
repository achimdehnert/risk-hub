"""Risk assessment services."""

from dataclasses import dataclass
from uuid import UUID

from bfagent_core import emit_audit_event, emit_outbox_event, get_context
from django.db import transaction
from django.utils import timezone

from permissions.authz import require_permission
from risk.models import Assessment


@dataclass(frozen=True)
class CreateAssessmentCmd:
    """Command to create an assessment."""
    title: str
    description: str = ""
    category: str = "general"
    site_id: UUID | None = None


@dataclass(frozen=True)
class ApproveAssessmentCmd:
    """Command to approve an assessment."""
    assessment_id: UUID


def list_assessments(limit: int = 100) -> list[Assessment]:
    ctx = get_context()
    if ctx.tenant_id is None:
        raise ValueError("Tenant required")

    require_permission("risk.assessment.read")

    return list(
        Assessment.objects.filter(tenant_id=ctx.tenant_id)
        .order_by("-created_at")[:limit]
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
        raise ValueError(
            f"Cannot approve assessment in status: {assessment.status}"
        )

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


async def analyze_hazard_with_ai(hazard_description: str) -> str:
    """Analyze hazard using AI."""
    from bfagent_llm import PromptFramework

    framework = PromptFramework.get_instance()

    result = await framework.execute(
        system_prompt=(
            "Du bist ein Experte für Gefährdungsbeurteilungen und "
            "Arbeitssicherheit.\n"
            "Analysiere die beschriebene Gefährdung und gib Empfehlungen "
            "für Schutzmaßnahmen."
        ),
        user_prompt=(
            "Analysiere folgende Gefährdung und schlage geeignete "
            "Schutzmaßnahmen vor:\n\n"
            "{{ hazard }}\n\n"
            "Bitte strukturiere deine Antwort wie folgt:\n"
            "1. Risikoeinschätzung\n"
            "2. Empfohlene Schutzmaßnahmen\n"
            "3. Priorität der Maßnahmen"
        ),
        context={"hazard": hazard_description},
        tier="standard",
    )

    if result.success and result.response:
        return result.response.content

    return f"Analyse fehlgeschlagen: {result.error}"
