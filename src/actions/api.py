from datetime import date, datetime
from uuid import UUID

from ninja import Router, Schema
from ninja.errors import HttpError

from actions.models import ActionItem
from actions.services import (
    CreateActionCmd,
    create_action,
    get_action,
    list_actions,
)
from permissions.authz import PermissionDenied

router = Router(tags=["actions"])


class ActionOut(Schema):
    id: UUID
    tenant_id: UUID
    title: str
    description: str
    status: str
    priority: int
    due_date: date | None
    assigned_to_id: UUID | None
    assessment_id: UUID | None
    hazard_id: UUID | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class ActionCreateIn(Schema):
    title: str
    description: str = ""
    status: str = "open"
    priority: int = 2
    due_date: date | None = None
    assigned_to_id: UUID | None = None
    assessment_id: UUID | None = None
    hazard_id: UUID | None = None


def _to_action_out(a: ActionItem) -> ActionOut:
    return ActionOut(
        id=a.id,
        tenant_id=a.tenant_id,
        title=a.title,
        description=a.description,
        status=a.status,
        priority=a.priority,
        due_date=a.due_date,
        assigned_to_id=a.assigned_to_id,
        assessment_id=a.assessment_id,
        hazard_id=a.hazard_id,
        created_at=a.created_at,
        updated_at=a.updated_at,
        completed_at=a.completed_at,
    )


@router.get("", response=list[ActionOut])
def api_list_actions(request, limit: int = 100):
    try:
        return [_to_action_out(a) for a in list_actions(limit=limit)]
    except PermissionDenied as exc:
        raise HttpError(403, str(exc))


@router.post("", response=ActionOut)
def api_create_action(request, payload: ActionCreateIn):
    try:
        action = create_action(
            CreateActionCmd(
                title=payload.title,
                description=payload.description,
                status=payload.status,
                priority=payload.priority,
                due_date=payload.due_date,
                assigned_to_id=payload.assigned_to_id,
                assessment_id=payload.assessment_id,
                hazard_id=payload.hazard_id,
            )
        )
        return _to_action_out(action)
    except PermissionDenied as exc:
        raise HttpError(403, str(exc))


@router.get("/{action_id}", response=ActionOut)
def api_get_action(request, action_id: UUID):
    try:
        return _to_action_out(get_action(action_id=action_id))
    except PermissionDenied as exc:
        raise HttpError(403, str(exc))
    except ActionItem.DoesNotExist:
        raise HttpError(404, "Not found")
