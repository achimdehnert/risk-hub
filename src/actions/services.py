from dataclasses import dataclass
from datetime import date
from uuid import UUID

from bfagent_core import get_context

from actions.models import ActionItem
from permissions.authz import require_permission


@dataclass(frozen=True)
class CreateActionCmd:
    title: str
    description: str = ""
    status: str = "open"
    priority: int = 2
    due_date: date | None = None
    assigned_to_id: UUID | None = None
    assessment_id: UUID | None = None
    hazard_id: UUID | None = None


def list_actions(limit: int = 100) -> list[ActionItem]:
    ctx = get_context()
    if ctx.tenant_id is None:
        raise ValueError("Tenant required")

    require_permission("actions.read")

    return list(
        ActionItem.objects.filter(tenant_id=ctx.tenant_id)
        .order_by("-created_at")[:limit]
    )


def get_action(action_id: UUID) -> ActionItem:
    ctx = get_context()
    if ctx.tenant_id is None:
        raise ValueError("Tenant required")

    require_permission("actions.read")

    return ActionItem.objects.get(
        id=action_id,
        tenant_id=ctx.tenant_id,
    )


def create_action(cmd: CreateActionCmd) -> ActionItem:
    ctx = get_context()
    if ctx.tenant_id is None:
        raise ValueError("Tenant required")

    require_permission("actions.write")

    return ActionItem.objects.create(
        tenant_id=ctx.tenant_id,
        title=cmd.title.strip(),
        description=cmd.description,
        status=cmd.status,
        priority=cmd.priority,
        due_date=cmd.due_date,
        assigned_to_id=cmd.assigned_to_id,
        assessment_id=cmd.assessment_id,
        hazard_id=cmd.hazard_id,
    )
