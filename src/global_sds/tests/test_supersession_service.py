# src/global_sds/tests/test_supersession_service.py
"""Tests for SdsSupersessionService (ADR-012 §6.2)."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from global_sds.models import GlobalSdsRevision, ImpactLevel
from global_sds.services.supersession_service import SdsSupersessionService
from global_sds.sds_usage import SdsUsage, SdsUsageStatus
from global_sds.tests.factories import (
    GlobalSdsRevisionFactory,
    GlobalSubstanceFactory,
    SdsRevisionDiffRecordFactory,
    SdsUsageFactory,
)


pytestmark = pytest.mark.django_db


class TestSupersede:
    """Core supersession logic."""

    def test_should_set_old_revision_to_superseded(self, db):
        substance = GlobalSubstanceFactory()
        old = GlobalSdsRevisionFactory(
            substance=substance, status="VERIFIED", source_hash="o" * 64,
        )
        new = GlobalSdsRevisionFactory(
            substance=substance, status="PENDING", source_hash="n" * 64,
        )
        diff = SdsRevisionDiffRecordFactory(
            old_revision=old, new_revision=new,
            overall_impact=ImpactLevel.INFORMATIONAL,
        )

        svc = SdsSupersessionService()
        svc.supersede(old, new, diff)

        old.refresh_from_db()
        new.refresh_from_db()
        assert old.status == GlobalSdsRevision.Status.SUPERSEDED
        assert old.superseded_by == new
        assert new.status == GlobalSdsRevision.Status.VERIFIED

    def test_should_return_affected_usage_count(self, db, user):
        substance = GlobalSubstanceFactory()
        old = GlobalSdsRevisionFactory(
            substance=substance, status="VERIFIED", source_hash="o" * 64,
        )
        new = GlobalSdsRevisionFactory(
            substance=substance, status="PENDING", source_hash="n" * 64,
        )
        diff = SdsRevisionDiffRecordFactory(
            old_revision=old, new_revision=new,
            overall_impact=ImpactLevel.REGULATORY,
        )
        # Create 3 active usages from different tenants
        for _ in range(3):
            SdsUsageFactory(sds_revision=old, status=SdsUsageStatus.ACTIVE, approved_by=user)

        svc = SdsSupersessionService()
        affected = svc.supersede(old, new, diff)
        assert affected == 3


class TestImpactHandling:
    """Status transitions based on impact level."""

    def test_should_set_review_required_for_safety_critical(self, db, user):
        substance = GlobalSubstanceFactory()
        old = GlobalSdsRevisionFactory(
            substance=substance, status="VERIFIED", source_hash="o" * 64,
        )
        new = GlobalSdsRevisionFactory(
            substance=substance, status="PENDING", source_hash="n" * 64,
        )
        diff = SdsRevisionDiffRecordFactory(
            old_revision=old, new_revision=new,
            overall_impact=ImpactLevel.SAFETY_CRITICAL,
        )
        usage = SdsUsageFactory(
            sds_revision=old, status=SdsUsageStatus.ACTIVE, approved_by=user,
        )

        svc = SdsSupersessionService()
        svc.supersede(old, new, diff)

        usage.refresh_from_db()
        assert usage.status == SdsUsageStatus.REVIEW_REQUIRED
        assert usage.pending_update_revision == new
        assert usage.pending_update_impact == ImpactLevel.SAFETY_CRITICAL

    def test_should_set_review_deadline_28_days(self, db, user):
        substance = GlobalSubstanceFactory()
        old = GlobalSdsRevisionFactory(
            substance=substance, status="VERIFIED", source_hash="o" * 64,
        )
        new = GlobalSdsRevisionFactory(
            substance=substance, status="PENDING", source_hash="n" * 64,
        )
        diff = SdsRevisionDiffRecordFactory(
            old_revision=old, new_revision=new,
            overall_impact=ImpactLevel.SAFETY_CRITICAL,
        )
        usage = SdsUsageFactory(
            sds_revision=old, status=SdsUsageStatus.ACTIVE, approved_by=user,
        )

        svc = SdsSupersessionService()
        svc.supersede(old, new, diff)

        usage.refresh_from_db()
        expected = date.today() + timedelta(days=28)
        assert usage.review_deadline == expected

    def test_should_set_update_available_for_regulatory(self, db, user):
        substance = GlobalSubstanceFactory()
        old = GlobalSdsRevisionFactory(
            substance=substance, status="VERIFIED", source_hash="o" * 64,
        )
        new = GlobalSdsRevisionFactory(
            substance=substance, status="PENDING", source_hash="n" * 64,
        )
        diff = SdsRevisionDiffRecordFactory(
            old_revision=old, new_revision=new,
            overall_impact=ImpactLevel.REGULATORY,
        )
        usage = SdsUsageFactory(
            sds_revision=old, status=SdsUsageStatus.ACTIVE, approved_by=user,
        )

        svc = SdsSupersessionService()
        svc.supersede(old, new, diff)

        usage.refresh_from_db()
        assert usage.status == SdsUsageStatus.UPDATE_AVAILABLE

    def test_should_not_change_status_for_informational(self, db, user):
        substance = GlobalSubstanceFactory()
        old = GlobalSdsRevisionFactory(
            substance=substance, status="VERIFIED", source_hash="o" * 64,
        )
        new = GlobalSdsRevisionFactory(
            substance=substance, status="PENDING", source_hash="n" * 64,
        )
        diff = SdsRevisionDiffRecordFactory(
            old_revision=old, new_revision=new,
            overall_impact=ImpactLevel.INFORMATIONAL,
        )
        usage = SdsUsageFactory(
            sds_revision=old, status=SdsUsageStatus.ACTIVE, approved_by=user,
        )

        svc = SdsSupersessionService()
        svc.supersede(old, new, diff)

        usage.refresh_from_db()
        assert usage.status == SdsUsageStatus.ACTIVE


class TestDownstreamFlagging:
    """GBU + Ex-Schutz flagging for SAFETY_CRITICAL."""

    @patch("global_sds.services.supersession_service.SdsSupersessionService._flag_downstream")
    def test_should_call_flag_downstream_for_safety_critical(self, mock_flag, db, user):
        substance = GlobalSubstanceFactory()
        old = GlobalSdsRevisionFactory(
            substance=substance, status="VERIFIED", source_hash="o" * 64,
        )
        new = GlobalSdsRevisionFactory(
            substance=substance, status="PENDING", source_hash="n" * 64,
        )
        diff = SdsRevisionDiffRecordFactory(
            old_revision=old, new_revision=new,
            overall_impact=ImpactLevel.SAFETY_CRITICAL,
        )

        svc = SdsSupersessionService()
        svc.supersede(old, new, diff)

        mock_flag.assert_called_once_with(old, diff)

    @patch("global_sds.services.supersession_service.SdsSupersessionService._flag_downstream")
    def test_should_not_flag_downstream_for_regulatory(self, mock_flag, db, user):
        substance = GlobalSubstanceFactory()
        old = GlobalSdsRevisionFactory(
            substance=substance, status="VERIFIED", source_hash="o" * 64,
        )
        new = GlobalSdsRevisionFactory(
            substance=substance, status="PENDING", source_hash="n" * 64,
        )
        diff = SdsRevisionDiffRecordFactory(
            old_revision=old, new_revision=new,
            overall_impact=ImpactLevel.REGULATORY,
        )

        svc = SdsSupersessionService()
        svc.supersede(old, new, diff)

        mock_flag.assert_not_called()
