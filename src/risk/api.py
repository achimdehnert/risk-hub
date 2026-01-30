from datetime import datetime
from uuid import UUID

from ninja import Router, Schema
from ninja.errors import HttpError

from permissions.authz import PermissionDenied
from risk.services import (
    ApproveAssessmentCmd,
    CreateAssessmentCmd,
    approve_assessment,
    create_assessment,
    get_assessment,
    list_assessments,
)

router = Router(tags=["risk"])


class AssessmentOut(Schema):
    id: UUID
    tenant_id: UUID
    title: str
    description: str
    category: str
    status: str
    site_id: UUID | None
    created_by_id: UUID | None
    approved_by_id: UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AssessmentCreateIn(Schema):
    title: str
    description: str = ""
    category: str = "general"
    site_id: UUID | None = None


def _to_assessment_out(a) -> AssessmentOut:
    return AssessmentOut(
        id=a.id,
        tenant_id=a.tenant_id,
        title=a.title,
        description=a.description,
        category=a.category,
        status=a.status,
        site_id=a.site_id,
        created_by_id=a.created_by_id,
        approved_by_id=a.approved_by_id,
        approved_at=a.approved_at,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


@router.get("/assessments", response=list[AssessmentOut])
def api_list_assessments(request, limit: int = 100):
    try:
        return [_to_assessment_out(a) for a in list_assessments(limit=limit)]
    except PermissionDenied as exc:
        raise HttpError(403, str(exc))


@router.post("/assessments", response=AssessmentOut)
def api_create_assessment(request, payload: AssessmentCreateIn):
    try:
        assessment = create_assessment(
            CreateAssessmentCmd(
                title=payload.title,
                description=payload.description,
                category=payload.category,
                site_id=payload.site_id,
            )
        )
        return _to_assessment_out(assessment)
    except PermissionDenied as exc:
        raise HttpError(403, str(exc))


@router.get("/assessments/{assessment_id}", response=AssessmentOut)
def api_get_assessment(request, assessment_id: UUID):
    try:
        return _to_assessment_out(get_assessment(assessment_id=assessment_id))
    except PermissionDenied as exc:
        raise HttpError(403, str(exc))
    except Exception:
        raise HttpError(404, "Not found")


@router.post("/assessments/{assessment_id}/approve", response=AssessmentOut)
def api_approve_assessment(request, assessment_id: UUID):
    try:
        assessment = approve_assessment(
            ApproveAssessmentCmd(
                assessment_id=assessment_id,
            )
        )
        return _to_assessment_out(assessment)
    except PermissionDenied as exc:
        raise HttpError(403, str(exc))
    except Exception as exc:
        raise HttpError(400, str(exc))
