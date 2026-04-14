# tests/test_progress_gbu.py
"""Tests für GbuProgressService."""

import datetime
from unittest.mock import MagicMock

from common.progress.base import StepState
from gbu.services.progress import GbuProgressService


def _make_activity(**overrides):
    """Create a mock HazardAssessmentActivity with sensible defaults."""
    defaults = {
        "sds_revision_id": 1,
        "site_id": 1,
        "activity_description": "Reinigung mit Aceton",
        "activity_frequency": "daily",
        "duration_minutes": 30,
        "quantity_class": "m",
        "substitution_checked": False,
        "substitution_notes": "",
        "risk_score": "",
        "approved_by_name": "",
        "next_review_date": None,
    }
    defaults.update(overrides)

    activity = MagicMock()
    for k, v in defaults.items():
        setattr(activity, k, v)

    # derived_hazard_categories — default empty
    cats_qs = MagicMock()
    cats_qs.values_list.return_value = overrides.get("_cat_types", [])
    activity.derived_hazard_categories = cats_qs

    # measures — default empty
    measures_qs = MagicMock()
    measures_list = overrides.get("_measures", [])
    measures_qs.all.return_value = measures_list
    activity.measures = measures_qs

    return activity


def _make_measure(tops_type="T"):
    m = MagicMock()
    m.tops_type = tops_type
    return m


class TestGbuStep1SubstanceSite:
    def test_should_complete_with_sds_and_site(self):
        svc = GbuProgressService()
        a = _make_activity()
        p = svc.get_progress(a)
        assert p.step_by_number(1).state == StepState.COMPLETE

    def test_should_empty_without_sds_and_site(self):
        svc = GbuProgressService()
        a = _make_activity(sds_revision_id=None, site_id=None)
        p = svc.get_progress(a)
        assert p.step_by_number(1).state == StepState.EMPTY

    def test_should_partial_without_site(self):
        svc = GbuProgressService()
        a = _make_activity(site_id=None)
        p = svc.get_progress(a)
        assert p.step_by_number(1).state == StepState.PARTIAL


class TestGbuStep2ActivityData:
    def test_should_complete_with_all_fields(self):
        svc = GbuProgressService()
        a = _make_activity()
        p = svc.get_progress(a)
        assert p.step_by_number(2).state == StepState.COMPLETE

    def test_should_empty_with_no_data(self):
        svc = GbuProgressService()
        a = _make_activity(
            activity_description="",
            activity_frequency="",
            duration_minutes=0,
            quantity_class="",
        )
        p = svc.get_progress(a)
        assert p.step_by_number(2).state == StepState.EMPTY


class TestGbuStep3HazardCategories:
    def test_should_complete_with_categories(self):
        svc = GbuProgressService()
        a = _make_activity(_cat_types=["INHALATION", "DERMAL"])
        p = svc.get_progress(a)
        step = p.step_by_number(3)
        assert step.state == StepState.COMPLETE
        assert step.item_count == 2

    def test_should_empty_without_categories(self):
        svc = GbuProgressService()
        a = _make_activity(_cat_types=[])
        p = svc.get_progress(a)
        assert p.step_by_number(3).state == StepState.EMPTY


class TestGbuStep4Substitution:
    def test_should_complete_for_non_cmr_unchecked(self):
        svc = GbuProgressService()
        a = _make_activity(_cat_types=["INHALATION"])
        p = svc.get_progress(a)
        assert p.step_by_number(4).state == StepState.COMPLETE

    def test_should_block_cmr_unchecked(self):
        svc = GbuProgressService()
        a = _make_activity(_cat_types=["CMR"])
        p = svc.get_progress(a)
        assert p.step_by_number(4).state == StepState.BLOCKED

    def test_should_complete_cmr_checked_with_notes(self):
        svc = GbuProgressService()
        a = _make_activity(
            _cat_types=["CMR"],
            substitution_checked=True,
            substitution_notes="Nicht substituierbar",
        )
        p = svc.get_progress(a)
        assert p.step_by_number(4).state == StepState.COMPLETE


class TestGbuStep5Measures:
    def test_should_empty_without_measures(self):
        svc = GbuProgressService()
        a = _make_activity()
        p = svc.get_progress(a)
        assert p.step_by_number(5).state == StepState.EMPTY

    def test_should_complete_with_tops_measures(self):
        svc = GbuProgressService()
        a = _make_activity(_measures=[
            _make_measure("T"),
            _make_measure("O"),
            _make_measure("S"),
        ])
        p = svc.get_progress(a)
        assert p.step_by_number(5).state == StepState.COMPLETE

    def test_should_error_psa_only_without_tech(self):
        svc = GbuProgressService()
        a = _make_activity(_measures=[_make_measure("P")])
        p = svc.get_progress(a)
        assert p.step_by_number(5).state == StepState.ERROR


class TestGbuStep7Effectiveness:
    def test_should_empty_without_review_date(self):
        svc = GbuProgressService()
        a = _make_activity()
        p = svc.get_progress(a)
        assert p.step_by_number(7).state == StepState.EMPTY

    def test_should_complete_with_future_date(self):
        svc = GbuProgressService()
        future = datetime.date.today() + datetime.timedelta(days=180)
        a = _make_activity(next_review_date=future)
        p = svc.get_progress(a)
        assert p.step_by_number(7).state == StepState.COMPLETE

    def test_should_error_with_past_date(self):
        svc = GbuProgressService()
        past = datetime.date.today() - datetime.timedelta(days=30)
        a = _make_activity(next_review_date=past)
        p = svc.get_progress(a)
        assert p.step_by_number(7).state == StepState.ERROR


class TestGbuStep8Approval:
    def test_should_empty_without_approver(self):
        svc = GbuProgressService()
        a = _make_activity()
        p = svc.get_progress(a)
        assert p.step_by_number(8).state == StepState.EMPTY

    def test_should_complete_with_approver(self):
        svc = GbuProgressService()
        a = _make_activity(approved_by_name="Dr. Müller")
        p = svc.get_progress(a)
        assert p.step_by_number(8).state == StepState.COMPLETE

    def test_should_warn_cmr_without_physician(self):
        svc = GbuProgressService()
        a = _make_activity(_cat_types=["CMR"])
        p = svc.get_progress(a)
        step = p.step_by_number(8)
        assert any("Betriebsarzt" in w for w in step.warnings)


class TestGbuCanApprove:
    def test_should_approve_all_complete(self):
        svc = GbuProgressService()
        future = datetime.date.today() + datetime.timedelta(days=180)
        a = _make_activity(
            _cat_types=["INHALATION"],
            _measures=[_make_measure("T"), _make_measure("S")],
            next_review_date=future,
            approved_by_name="Dr. Müller",
        )
        p = svc.get_progress(a)
        assert p.can_approve is True
        assert p.overall_percent == 100

    def test_should_not_approve_with_blocked_step(self):
        svc = GbuProgressService()
        a = _make_activity(_cat_types=["CMR"])  # CMR blocks step 4
        p = svc.get_progress(a)
        assert p.can_approve is False
