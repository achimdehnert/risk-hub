"""
Tests für GBU Phase 2F — Django Ninja API.

Getestet werden:
  - GET  /api/v1/gbu/activities        — list (mit + ohne Status-Filter)
  - POST /api/v1/gbu/activities        — create
  - GET  /api/v1/gbu/activities/{id}   — detail
  - POST /api/v1/gbu/activities/{id}/approve — approve
  - GET  /api/v1/gbu/compliance        — compliance-summary

Mocking:
  - ApiKeyAuth → direkt via test_client mit force_authenticate-äquivalent
  - Celery-Task generate_documents_task → gepatch
  - emit_audit_event → gepatch (kein Outbox-Setup nötig)
"""

import uuid
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.test import Client

# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def user_id():
    return uuid.uuid4()


@pytest.fixture
def api_context(tenant_id, user_id):
    """Setzt common.context für API-Calls ohne echten ApiKey."""
    from common.context import set_tenant, set_user_id

    set_tenant(tenant_id, None)
    set_user_id(user_id)
    return {"tenant_id": tenant_id, "user_id": user_id}


@pytest.fixture
def gbu_client(api_context):
    """Django-Testclient mit gesetztem Context."""
    return Client()


@pytest.fixture
def activity(db, tenant_id, user_id):
    """Approved HazardAssessmentActivity für Tests."""

    from gbu.models.activity import ActivityStatus, HazardAssessmentActivity
    from substances.models import SdsRevision, Substance
    from tenancy.models import Organization, Site

    org, _ = Organization.objects.get_or_create(
        tenant_id=tenant_id,
        defaults={"name": "Test Org", "slug": f"test-{tenant_id}"},
    )
    site, _ = Site.objects.get_or_create(
        tenant_id=tenant_id,
        defaults={"name": "Teststandort", "organization": org},
    )
    substance, _ = Substance.objects.get_or_create(
        tenant_id=tenant_id,
        name="Testaceton",
        defaults={"cas_number": "67-64-1"},
    )
    revision, _ = SdsRevision.objects.get_or_create(
        tenant_id=tenant_id,
        substance=substance,
        revision_number=1,
        defaults={"language": "de"},
    )
    return HazardAssessmentActivity.objects.create(
        tenant_id=tenant_id,
        site=site,
        sds_revision=revision,
        activity_description="Reinigung mit Lösungsmittel",
        activity_frequency="weekly",
        duration_minutes=30,
        quantity_class="s",
        status=ActivityStatus.DRAFT,
        created_by=user_id,
    )


# ── Tests: list_activities ────────────────────────────────────────────────


@pytest.mark.django_db
def test_should_list_activities_for_tenant(db, api_context, activity):
    """api_list_activities soll Tätigkeiten des Tenants zurückgeben."""
    from gbu.api import api_list_activities

    class FakeRequest:
        pass

    result = api_list_activities(FakeRequest(), status=None, limit=100, offset=0)
    ids = [r.id for r in result]
    assert activity.id in ids


@pytest.mark.django_db
def test_should_filter_activities_by_status(db, api_context, activity):
    """api_list_activities mit status-Filter soll nur passende zurückgeben."""
    from gbu.api import api_list_activities

    class FakeRequest:
        pass

    result = api_list_activities(FakeRequest(), status="draft", limit=100, offset=0)
    assert all(r.status == "draft" for r in result)

    result_approved = api_list_activities(FakeRequest(), status="approved", limit=100, offset=0)
    ids = [r.id for r in result_approved]
    assert activity.id not in ids


# ── Tests: get_activity ───────────────────────────────────────────────────


@pytest.mark.django_db
def test_should_get_activity_detail(db, api_context, activity):
    """api_get_activity soll korrekte ActivityOut zurückgeben."""
    from gbu.api import api_get_activity

    class FakeRequest:
        pass

    result = api_get_activity(FakeRequest(), activity_id=activity.id)
    assert result.id == activity.id
    assert result.activity_description == activity.activity_description


@pytest.mark.django_db
def test_should_raise_404_for_unknown_activity(db, api_context):
    """api_get_activity soll 404 werfen für unbekannte ID."""
    from ninja.errors import HttpError

    from gbu.api import api_get_activity

    class FakeRequest:
        pass

    with pytest.raises(HttpError) as exc_info:
        api_get_activity(FakeRequest(), activity_id=uuid.uuid4())
    assert exc_info.value.status_code == 404


# ── Tests: create_activity ───────────────────────────────────────────────


@pytest.mark.django_db
def test_should_create_activity_via_api(db, api_context, activity):
    """api_create_activity soll neue Aktivität mit DRAFT-Status erzeugen."""
    from gbu.api import ActivityCreateIn, api_create_activity
    from gbu.models.activity import ActivityStatus

    class FakeRequest:
        pass

    payload = ActivityCreateIn(
        site_id=activity.site_id,
        sds_revision_id=activity.sds_revision_id,
        activity_description="API-Test-Tätigkeit",
        activity_frequency="occasional",
        duration_minutes=15,
        quantity_class="xs",
    )

    with (
        patch("gbu.services.gbu_engine.emit_audit_event"),
        patch("gbu.models.reference.ExposureRiskMatrix.objects"),
    ):
        result = api_create_activity(FakeRequest(), payload=payload)

    assert result.activity_description == "API-Test-Tätigkeit"
    assert result.status == ActivityStatus.DRAFT


# ── Tests: approve_activity ──────────────────────────────────────────────


@pytest.mark.django_db
def test_should_approve_activity_via_api(db, api_context, activity):
    """api_approve_activity soll Status auf APPROVED setzen."""
    from gbu.api import ActivityApproveIn, api_approve_activity
    from gbu.models.activity import ActivityStatus

    class FakeRequest:
        pass

    payload = ActivityApproveIn(
        next_review_date=date.today() + timedelta(days=365),
        approved_by_name="API-Tester",
    )

    with (
        patch("gbu.services.gbu_engine.emit_audit_event"),
        patch("gbu.tasks.generate_documents_task") as mock_task,
    ):
        mock_task.delay.return_value = None
        result = api_approve_activity(FakeRequest(), activity_id=activity.id, payload=payload)

    assert result.status == ActivityStatus.APPROVED
    assert result.approved_by_name == "API-Tester"
    mock_task.delay.assert_called_once()


# ── Tests: compliance ─────────────────────────────────────────────────────


@pytest.mark.django_db
def test_should_return_compliance_summary(db, api_context):
    """api_compliance_status soll ComplianceOut mit korrekten Feldern liefern."""
    from gbu.api import api_compliance_status

    class FakeRequest:
        pass

    result = api_compliance_status(FakeRequest())
    assert hasattr(result, "total_approved")
    assert hasattr(result, "overdue")
    assert hasattr(result, "due_soon")
    assert hasattr(result, "has_issues")
    assert result.total_approved == 0
