# src/global_sds/tests/test_version_detector.py
"""Tests for SdsVersionDetector (ADR-012 §5 Stufe 3)."""

from datetime import date

import pytest

from global_sds.services.version_detector import (
    SdsVersionDetector,
    VersionOutcome,
)
from global_sds.tests.factories import GlobalSdsRevisionFactory

pytestmark = pytest.mark.django_db


class TestFirstRevision:
    """No existing revisions → FIRST_REVISION."""

    def test_should_detect_first_revision(self, substance_acetone):
        detector = SdsVersionDetector()
        result = detector.detect(
            substance=substance_acetone,
            revision_date=date(2025, 1, 1),
            version_number="1.0",
        )
        assert result.outcome == VersionOutcome.FIRST_REVISION
        assert result.previous_revision is None


class TestNewRevision:
    """Newer date or higher version → NEW_REVISION."""

    def test_should_detect_new_revision_by_date(
        self,
        substance_acetone,
        revision_acetone_v1,
    ):
        detector = SdsVersionDetector()
        result = detector.detect(
            substance=substance_acetone,
            revision_date=date(2025, 6, 1),
            version_number="",
        )
        assert result.outcome == VersionOutcome.NEW_REVISION
        assert result.previous_revision == revision_acetone_v1

    def test_should_detect_new_revision_by_version(
        self,
        substance_acetone,
        revision_acetone_v1,
    ):
        detector = SdsVersionDetector()
        result = detector.detect(
            substance=substance_acetone,
            revision_date=None,
            version_number="2.0",
        )
        assert result.outcome == VersionOutcome.NEW_REVISION
        assert result.previous_revision == revision_acetone_v1


class TestConflict:
    """Retrograde date or ambiguous version → CONFLICT."""

    def test_should_detect_conflict_retrograde_date(
        self,
        substance_acetone,
        revision_acetone_v1,
    ):
        detector = SdsVersionDetector()
        result = detector.detect(
            substance=substance_acetone,
            revision_date=date(2023, 1, 1),
            version_number="",
        )
        assert result.outcome == VersionOutcome.CONFLICT
        assert result.previous_revision == revision_acetone_v1

    def test_should_detect_conflict_same_version_different_content(
        self,
        substance_acetone,
        revision_acetone_v1,
    ):
        """Same date + same version = CONFLICT (not a new revision)."""
        detector = SdsVersionDetector()
        result = detector.detect(
            substance=substance_acetone,
            revision_date=None,  # skip date comparison
            version_number="1.0",  # same as v1
        )
        assert result.outcome == VersionOutcome.CONFLICT

    def test_should_detect_conflict_no_date_no_version(
        self,
        substance_acetone,
        revision_acetone_v1,
    ):
        detector = SdsVersionDetector()
        result = detector.detect(
            substance=substance_acetone,
            revision_date=None,
            version_number="",
        )
        assert result.outcome == VersionOutcome.CONFLICT


class TestEdgeCases:
    """Edge cases and robustness."""

    def test_should_handle_unparseable_version(
        self,
        substance_acetone,
        revision_acetone_v1,
    ):
        detector = SdsVersionDetector()
        result = detector.detect(
            substance=substance_acetone,
            revision_date=None,
            version_number="abc.xyz",
        )
        # Unparseable → falls through to CONFLICT
        assert result.outcome == VersionOutcome.CONFLICT

    def test_should_skip_rejected_revisions(self, substance_acetone, tenant_id):
        """Rejected revisions should not count as 'current'."""
        GlobalSdsRevisionFactory(
            substance=substance_acetone,
            status="REJECTED",
            uploaded_by_tenant_id=tenant_id,
            revision_date=date(2024, 6, 1),
            version_number="1.0",
        )
        detector = SdsVersionDetector()
        result = detector.detect(
            substance=substance_acetone,
            revision_date=date(2025, 1, 1),
            version_number="1.0",
        )
        assert result.outcome == VersionOutcome.FIRST_REVISION
