"""Unit-Tests für GBU-Engine Phase 2B (calculate_risk_score, approve_activity)."""
import datetime
import uuid

import pytest

from gbu.models.reference import ExposureRiskMatrix
from gbu.services.gbu_engine import calculate_risk_score

# ── ExposureRiskMatrix Model-Tests ────────────────────────────────────────────

def test_should_exposure_risk_matrix_str_contain_risk_score():
    entry = ExposureRiskMatrix(
        quantity_class="m",
        activity_frequency="daily",
        has_cmr=False,
        risk_score="high",
    )
    assert "high" in str(entry)
    assert "m/daily" in str(entry)


def test_should_exposure_risk_matrix_str_contain_cmr_flag():
    entry = ExposureRiskMatrix(
        quantity_class="s",
        activity_frequency="weekly",
        has_cmr=True,
        risk_score="critical",
    )
    assert "[CMR]" in str(entry)


# ── calculate_risk_score Tests ────────────────────────────────────────────────

@pytest.mark.django_db
def test_should_calculate_risk_score_return_db_value():
    ExposureRiskMatrix.objects.create(
        quantity_class="xs",
        activity_frequency="rare",
        has_cmr=False,
        risk_score="low",
        emkg_class="A",
    )
    result = calculate_risk_score("xs", "rare", has_cmr=False)
    assert result == "low"


@pytest.mark.django_db
def test_should_calculate_risk_score_return_high_for_cmr():
    ExposureRiskMatrix.objects.create(
        quantity_class="xs",
        activity_frequency="rare",
        has_cmr=True,
        risk_score="high",
        emkg_class="C",
    )
    result = calculate_risk_score("xs", "rare", has_cmr=True)
    assert result == "high"


@pytest.mark.django_db
def test_should_calculate_risk_score_fallback_to_high_if_no_entry():
    """Kein Eintrag in Matrix → Fail-safe Fallback 'high'."""
    result = calculate_risk_score("l", "daily", has_cmr=False)
    assert result == "high"


@pytest.mark.django_db
def test_should_calculate_risk_score_critical_for_large_cmr_daily():
    ExposureRiskMatrix.objects.create(
        quantity_class="l",
        activity_frequency="daily",
        has_cmr=True,
        risk_score="critical",
        emkg_class="C",
    )
    result = calculate_risk_score("l", "daily", has_cmr=True)
    assert result == "critical"


# ── approve_activity Tests ─────────────────────────────────────────────────────

@pytest.mark.django_db
def test_should_approve_activity_set_status_and_snapshot(mocker):
    """approve_activity setzt Status, approved_by_id, approved_by_name."""
    from gbu.models.activity import ActivityStatus, HazardAssessmentActivity
    from gbu.services.gbu_engine import ApproveActivityCmd, approve_activity

    mocker.patch("gbu.services.gbu_engine.emit_audit_event")

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    activity = HazardAssessmentActivity(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        activity_description="Testarbeit",
        activity_frequency="daily",
        duration_minutes=60,
        quantity_class="s",
        status=ActivityStatus.DRAFT,
    )

    mocker.patch(
        "gbu.services.gbu_engine.HazardAssessmentActivity.objects"
        ".select_for_update"
    ).return_value.get.return_value = activity

    save_mock = mocker.patch.object(activity, "save")

    cmd = ApproveActivityCmd(
        activity_id=activity.id,
        next_review_date=datetime.date(2027, 1, 1),
    )

    result = approve_activity(
        cmd=cmd,
        tenant_id=tenant_id,
        user_id=user_id,
        approved_by_name="Max Mustermann",
    )

    assert result.status == ActivityStatus.APPROVED
    assert result.approved_by_id == user_id
    assert result.approved_by_name == "Max Mustermann"
    assert result.next_review_date == datetime.date(2027, 1, 1)
    save_mock.assert_called_once()


@pytest.mark.django_db
def test_should_approve_activity_raise_for_already_approved(mocker):
    """Bereits freigegebene Tätigkeit kann nicht nochmals freigegeben werden."""
    from gbu.models.activity import ActivityStatus, HazardAssessmentActivity
    from gbu.services.gbu_engine import ApproveActivityCmd, approve_activity

    activity = HazardAssessmentActivity(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        status=ActivityStatus.APPROVED,
    )

    mocker.patch(
        "gbu.services.gbu_engine.HazardAssessmentActivity.objects"
        ".select_for_update"
    ).return_value.get.return_value = activity

    cmd = ApproveActivityCmd(
        activity_id=activity.id,
        next_review_date=datetime.date(2027, 1, 1),
    )

    with pytest.raises(ValueError, match="kann nicht freigegeben werden"):
        approve_activity(
            cmd=cmd,
            tenant_id=activity.tenant_id,
            user_id=uuid.uuid4(),
        )
