# tests/test_progress_base.py
"""Tests für BaseProgressService (common/progress)."""


from common.progress.base import (
    BaseProgressService,
    DocumentProgress,
    StepDef,
    StepState,
    StepStatus,
)

# ── Fixture: Concrete subclass for testing ─────────────────────────────────────


class _TestProgressService(BaseProgressService):
    """Minimal subclass for testing base behavior."""

    STEP_DEFS = [
        StepDef(1, "Step A", "_check_a", "Law §1"),
        StepDef(2, "Step B", "_check_b", "Law §2"),
        StepDef(3, "Step C", "_check_c", "Law §3"),
    ]

    def _check_a(self, doc, ctx):
        if doc.get("a_complete"):
            return self._complete(info=["A done"])
        return self._empty("A not started")

    def _check_b(self, doc, ctx):
        if doc.get("b_partial"):
            return self._partial(["B incomplete"], pct=50)
        if doc.get("b_complete"):
            return self._complete()
        return self._empty("B not started")

    def _check_c(self, doc, ctx):
        if doc.get("c_error"):
            return self._error(["C broken"])
        if doc.get("c_complete"):
            return self._complete()
        return self._blocked("C blocked by prerequisite")


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestStepStatus:
    def test_should_report_complete(self):
        s = StepStatus(step=1, label="X", state=StepState.COMPLETE)
        assert s.is_complete is True
        assert s.icon == "✓"
        assert s.css_class == "complete"

    def test_should_report_incomplete(self):
        s = StepStatus(step=1, label="X", state=StepState.PARTIAL)
        assert s.is_complete is False
        assert s.icon == "◐"

    def test_should_report_blocked(self):
        s = StepStatus(step=1, label="X", state=StepState.BLOCKED)
        assert s.is_complete is False
        assert s.icon == "!"


class TestDocumentProgress:
    def test_should_count_complete_steps(self):
        steps = [
            StepStatus(step=1, label="A", state=StepState.COMPLETE),
            StepStatus(step=2, label="B", state=StepState.PARTIAL),
            StepStatus(step=3, label="C", state=StepState.COMPLETE),
        ]
        dp = DocumentProgress(
            steps=steps, can_approve=False, blocking_reasons=["B"], overall_percent=67,
        )
        assert dp.complete_count == 2
        assert dp.error_count == 0
        assert dp.total_steps == 3

    def test_should_find_step_by_number(self):
        steps = [
            StepStatus(step=1, label="A", state=StepState.COMPLETE),
            StepStatus(step=2, label="B", state=StepState.ERROR),
        ]
        dp = DocumentProgress(
            steps=steps, can_approve=False, blocking_reasons=[], overall_percent=50,
        )
        assert dp.step_by_number(2).state == StepState.ERROR
        assert dp.step_by_number(99) is None
        assert dp.error_count == 1


class TestBaseProgressService:
    def test_should_return_all_empty_for_blank_document(self):
        svc = _TestProgressService()
        progress = svc.get_progress({})
        assert progress.total_steps == 3
        assert progress.can_approve is False
        assert progress.overall_percent == 0
        assert len(progress.blocking_reasons) == 3

    def test_should_approve_when_all_complete(self):
        svc = _TestProgressService()
        doc = {"a_complete": True, "b_complete": True, "c_complete": True}
        progress = svc.get_progress(doc)
        assert progress.can_approve is True
        assert progress.overall_percent == 100
        assert progress.blocking_reasons == []

    def test_should_block_when_one_step_incomplete(self):
        svc = _TestProgressService()
        doc = {"a_complete": True, "b_partial": True, "c_complete": True}
        progress = svc.get_progress(doc)
        assert progress.can_approve is False
        assert progress.overall_percent == 67  # 2/3 rounded

    def test_should_set_step_metadata_from_defs(self):
        svc = _TestProgressService()
        progress = svc.get_progress({"a_complete": True})
        step_a = progress.step_by_number(1)
        assert step_a.label == "Step A"
        assert step_a.law_reference == "Law §1"

    def test_should_report_error_steps(self):
        svc = _TestProgressService()
        doc = {"a_complete": True, "b_complete": True, "c_error": True}
        progress = svc.get_progress(doc)
        assert progress.can_approve is False
        assert progress.error_count == 1


class TestFactoryMethods:
    def test_should_create_empty_status(self):
        s = BaseProgressService._empty("not done")
        assert s.state == StepState.EMPTY
        assert s.issues == ["not done"]

    def test_should_create_partial_status(self):
        s = BaseProgressService._partial(["half done"], pct=50)
        assert s.state == StepState.PARTIAL
        assert s.completion_percent == 50

    def test_should_create_complete_status(self):
        s = BaseProgressService._complete(info=["all good"])
        assert s.state == StepState.COMPLETE
        assert s.completion_percent == 100

    def test_should_create_error_status(self):
        s = BaseProgressService._error(["broken"])
        assert s.state == StepState.ERROR

    def test_should_create_blocked_status(self):
        s = BaseProgressService._blocked("prerequisite missing")
        assert s.state == StepState.BLOCKED
