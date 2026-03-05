"""
Tests für GBU Phase 2E — Compliance-Service und Review-Deadline-Task.
"""

import uuid
from datetime import date, timedelta
from unittest.mock import patch

import pytest


# ── Hilfsfunktion ─────────────────────────────────────────────────────────


def _make_approved_activity(db, tenant_id, review_date, user_id=None):
    """Approved HazardAssessmentActivity mit gesetztem next_review_date."""
    from django.utils import timezone

    from substances.models import SdsRevision, Substance
    from tenancy.models import Organization, Site

    if user_id is None:
        user_id = uuid.uuid4()

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
        name=f"Stoff-{uuid.uuid4()}",
    )
    revision, _ = SdsRevision.objects.get_or_create(
        tenant_id=tenant_id,
        substance=substance,
        revision_number=1,
    )
    from gbu.models.activity import ActivityStatus, HazardAssessmentActivity

    return HazardAssessmentActivity.objects.create(
        tenant_id=tenant_id,
        site=site,
        sds_revision=revision,
        activity_description="Testaktivität",
        activity_frequency="weekly",
        duration_minutes=30,
        quantity_class="s",
        status=ActivityStatus.APPROVED,
        approved_by_id=user_id,
        approved_by_name="Max Mustermann",
        approved_at=timezone.now(),
        next_review_date=review_date,
        created_by=user_id,
    )


# ── list_due_reviews ──────────────────────────────────────────────


@pytest.mark.django_db
def test_should_list_activity_due_within_30_days(db):
    """list_due_reviews() soll Tätigkeiten mit Frist in 30 Tagen zurückgeben."""
    from gbu.services.compliance import list_due_reviews

    tenant_id = uuid.uuid4()
    due_date = date.today() + timedelta(days=15)
    act = _make_approved_activity(db, tenant_id, due_date)

    result = list_due_reviews(tenant_id)
    assert act in result


@pytest.mark.django_db
def test_should_not_list_activity_due_in_60_days(db):
    """list_due_reviews() soll Tätigkeiten mit Frist > 30 Tage NICHT listen."""
    from gbu.services.compliance import list_due_reviews

    tenant_id = uuid.uuid4()
    far_date = date.today() + timedelta(days=60)
    act = _make_approved_activity(db, tenant_id, far_date)

    result = list_due_reviews(tenant_id)
    assert act not in result


@pytest.mark.django_db
def test_should_not_list_overdue_in_due_reviews(db):
    """list_due_reviews() soll überfällige Tätigkeiten NICHT einschließen."""
    from gbu.services.compliance import list_due_reviews

    tenant_id = uuid.uuid4()
    past_date = date.today() - timedelta(days=5)
    act = _make_approved_activity(db, tenant_id, past_date)

    result = list_due_reviews(tenant_id)
    assert act not in result


# ── list_overdue_reviews ───────────────────────────────────────────


@pytest.mark.django_db
def test_should_list_overdue_activity(db):
    """list_overdue_reviews() soll Tätigkeiten mit past review date zurückgeben."""
    from gbu.services.compliance import list_overdue_reviews

    tenant_id = uuid.uuid4()
    past_date = date.today() - timedelta(days=10)
    act = _make_approved_activity(db, tenant_id, past_date)

    result = list_overdue_reviews(tenant_id)
    assert act in result


@pytest.mark.django_db
def test_should_not_list_future_as_overdue(db):
    """list_overdue_reviews() soll zukünftige Frist NICHT als überfällig listen."""
    from gbu.services.compliance import list_overdue_reviews

    tenant_id = uuid.uuid4()
    future_date = date.today() + timedelta(days=10)
    act = _make_approved_activity(db, tenant_id, future_date)

    result = list_overdue_reviews(tenant_id)
    assert act not in result


# ── mark_outdated_activities ───────────────────────────────────────────


@pytest.mark.django_db
def test_should_mark_overdue_as_outdated(db):
    """
    mark_outdated_activities() soll überfällige APPROVED-Tätigkeiten
    auf OUTDATED setzen.
    """
    from gbu.models.activity import ActivityStatus
    from gbu.services.compliance import mark_outdated_activities

    tenant_id = uuid.uuid4()
    past_date = date.today() - timedelta(days=5)

    with patch("common.context.emit_audit_event"):
        act = _make_approved_activity(db, tenant_id, past_date)
        count = mark_outdated_activities(tenant_id)

    act.refresh_from_db()
    assert count == 1
    assert act.status == ActivityStatus.OUTDATED


@pytest.mark.django_db
def test_should_not_mark_future_as_outdated(db):
    """mark_outdated_activities() soll zukünftige Fristen NICHT verändern."""
    from gbu.models.activity import ActivityStatus
    from gbu.services.compliance import mark_outdated_activities

    tenant_id = uuid.uuid4()
    future_date = date.today() + timedelta(days=10)

    with patch("common.context.emit_audit_event"):
        act = _make_approved_activity(db, tenant_id, future_date)
        count = mark_outdated_activities(tenant_id)

    act.refresh_from_db()
    assert count == 0
    assert act.status == ActivityStatus.APPROVED


# ── compliance_summary ──────────────────────────────────────────────


@pytest.mark.django_db
def test_should_return_correct_summary_counts(db):
    """
    compliance_summary() soll korrekte Zähler für overdue,
    due_soon und total_approved liefern.
    """
    from gbu.services.compliance import compliance_summary

    tenant_id = uuid.uuid4()
    _make_approved_activity(db, tenant_id, date.today() - timedelta(days=3))
    _make_approved_activity(db, tenant_id, date.today() + timedelta(days=10))
    _make_approved_activity(db, tenant_id, date.today() + timedelta(days=60))

    summary = compliance_summary(tenant_id)

    assert summary.overdue == 1
    assert summary.due_soon == 1
    assert summary.total_approved == 3
