"""
GBU API-Router (Phase 2F).

Endpoints:
  GET  /api/v1/gbu/activities              — Liste aller GBU-Tätigkeiten
  POST /api/v1/gbu/activities              — Neue Tätigkeit anlegen
  GET  /api/v1/gbu/activities/{id}         — Detail
  POST /api/v1/gbu/activities/{id}/approve — Tätigkeit freigeben
  GET  /api/v1/gbu/compliance              — Compliance-KPIs des Tenants

Auth: ApiKeyAuth (Bearer-Token) via config.api_auth
Tenant: wird aus ApiKey-Kontext gesetzt (common.context)
"""

import datetime
from uuid import UUID

from ninja import Router, Schema
from ninja.errors import HttpError

from permissions.authz import PermissionDenied

router = Router(tags=["gbu"])


# ── Schemas ─────────────────────────────────────────────────────────────


class ActivityOut(Schema):
    id: int
    tenant_id: UUID
    site_id: int
    sds_revision_id: int
    activity_description: str
    activity_frequency: str
    duration_minutes: int
    quantity_class: str
    substitution_checked: bool
    risk_score: str
    status: str
    approved_by_name: str
    approved_at: datetime.datetime | None
    next_review_date: datetime.date | None
    gbu_document_id: int | None
    ba_document_id: int | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ActivityCreateIn(Schema):
    site_id: int
    sds_revision_id: int
    activity_description: str
    activity_frequency: str
    duration_minutes: int
    quantity_class: str
    substitution_checked: bool = False
    substitution_notes: str = ""


class ActivityApproveIn(Schema):
    next_review_date: datetime.date
    approved_by_name: str = ""


class ComplianceOut(Schema):
    total_approved: int
    due_soon: int
    overdue: int
    outdated: int
    draft_count: int
    has_issues: bool


# ── Helpers ────────────────────────────────────────────────────────────


def _to_out(a) -> ActivityOut:
    return ActivityOut(
        id=a.id,
        tenant_id=a.tenant_id,
        site_id=a.site_id,
        sds_revision_id=a.sds_revision_id,
        activity_description=a.activity_description,
        activity_frequency=a.activity_frequency,
        duration_minutes=a.duration_minutes,
        quantity_class=a.quantity_class,
        substitution_checked=a.substitution_checked,
        risk_score=a.risk_score,
        status=a.status,
        approved_by_name=a.approved_by_name,
        approved_at=a.approved_at,
        next_review_date=a.next_review_date,
        gbu_document_id=a.gbu_document_id,
        ba_document_id=a.ba_document_id,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


def _tenant_id_from_context() -> UUID:
    from common.context import get_context

    ctx = get_context()
    if ctx.tenant_id is None:
        raise HttpError(403, "Tenant-Kontext fehlt")
    return ctx.tenant_id


def _user_id_from_context() -> UUID | None:
    from common.context import get_context

    return get_context().user_id


# ── Endpoints ───────────────────────────────────────────────────────────


@router.get("/activities", response=list[ActivityOut])
def api_list_activities(
    request,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Alle GBU-Tätigkeiten des Tenants.

    Optionaler Filter: ?status=draft|review|approved|outdated
    """
    from gbu.models.activity import HazardAssessmentActivity

    try:
        tenant_id = _tenant_id_from_context()
    except HttpError:
        raise
    except PermissionDenied as exc:
        raise HttpError(403, str(exc)) from exc

    qs = HazardAssessmentActivity.objects.filter(tenant_id=tenant_id).order_by("-created_at")
    if status:
        qs = qs.filter(status=status)

    return [_to_out(a) for a in qs[offset : offset + limit]]


@router.post("/activities", response=ActivityOut)
def api_create_activity(request, payload: ActivityCreateIn):
    """
    Neue GBU-Tätigkeit anlegen (Status: DRAFT).

    Risikoscore wird sofort berechnet.
    """
    from gbu.services.gbu_engine import (
        CreateActivityCmd,
        create_activity,
        set_risk_score,
    )

    try:
        tenant_id = _tenant_id_from_context()
        user_id = _user_id_from_context()
    except HttpError:
        raise
    except PermissionDenied as exc:
        raise HttpError(403, str(exc)) from exc

    try:
        cmd = CreateActivityCmd(
            site_id=payload.site_id,
            sds_revision_id=payload.sds_revision_id,
            activity_description=payload.activity_description,
            activity_frequency=payload.activity_frequency,
            duration_minutes=payload.duration_minutes,
            quantity_class=payload.quantity_class,
            substitution_checked=payload.substitution_checked,
            substitution_notes=payload.substitution_notes,
        )
        activity = create_activity(cmd=cmd, tenant_id=tenant_id, user_id=user_id)
        set_risk_score(activity_id=activity.id, tenant_id=tenant_id)
        activity.refresh_from_db()
        return _to_out(activity)
    except Exception as exc:
        raise HttpError(400, str(exc)) from exc


@router.get("/activities/{activity_id}", response=ActivityOut)
def api_get_activity(request, activity_id: int):
    """GBU-Tätigkeit Detail."""
    from gbu.models.activity import HazardAssessmentActivity

    try:
        tenant_id = _tenant_id_from_context()
    except HttpError:
        raise
    except PermissionDenied as exc:
        raise HttpError(403, str(exc)) from exc

    try:
        activity = HazardAssessmentActivity.objects.get(id=activity_id, tenant_id=tenant_id)
        return _to_out(activity)
    except HazardAssessmentActivity.DoesNotExist:
        raise HttpError(404, "GBU-Tätigkeit nicht gefunden") from None


@router.post("/activities/{activity_id}/approve", response=ActivityOut)
def api_approve_activity(request, activity_id: int, payload: ActivityApproveIn):
    """
    GBU-Tätigkeit freigeben.

    Setzt Status → APPROVED, löst Celery-Task zur PDF-Generierung aus.
    """
    from gbu.services.gbu_engine import ApproveActivityCmd, approve_activity
    from gbu.tasks import generate_documents_task

    try:
        tenant_id = _tenant_id_from_context()
        user_id = _user_id_from_context()
    except HttpError:
        raise
    except PermissionDenied as exc:
        raise HttpError(403, str(exc)) from exc

    if user_id is None:
        raise HttpError(403, "Authentifizierter Nutzer erforderlich")

    try:
        cmd = ApproveActivityCmd(
            activity_id=activity_id,
            next_review_date=payload.next_review_date,
        )
        activity = approve_activity(
            cmd=cmd,
            tenant_id=tenant_id,
            user_id=user_id,
            approved_by_name=payload.approved_by_name,
        )
        generate_documents_task.delay(str(activity_id), str(tenant_id))
        return _to_out(activity)
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
    except Exception as exc:
        raise HttpError(400, str(exc)) from exc


@router.get("/compliance", response=ComplianceOut)
def api_compliance_status(request):
    """Compliance-KPIs des Tenants (due, overdue, outdated)."""
    from gbu.services.compliance import compliance_summary

    try:
        tenant_id = _tenant_id_from_context()
    except HttpError:
        raise
    except PermissionDenied as exc:
        raise HttpError(403, str(exc)) from exc

    summary = compliance_summary(tenant_id)
    return ComplianceOut(
        total_approved=summary.total_approved,
        due_soon=summary.due_soon,
        overdue=summary.overdue,
        outdated=summary.outdated,
        draft_count=summary.draft_count,
        has_issues=summary.has_issues,
    )
