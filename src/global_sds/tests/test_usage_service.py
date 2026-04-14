# src/global_sds/tests/test_usage_service.py
"""Tests for SdsUsageService (ADR-012 §6.4)."""

from datetime import date

import pytest

from global_sds.services.usage_service import SdsUsageService
from global_sds.sds_usage import SdsUsage, SdsUsageStatus
from global_sds.tests.factories import (
    GlobalSdsRevisionFactory,
    GlobalSubstanceFactory,
    SdsUsageFactory,
)


pytestmark = pytest.mark.django_db


class TestAdoptUpdate:
    """adopt_update() — übernimmt neue Revision."""

    def test_should_create_new_usage_and_supersede_old(self, db, user):
        substance = GlobalSubstanceFactory()
        old_rev = GlobalSdsRevisionFactory(
            substance=substance, source_hash="o" * 64,
        )
        new_rev = GlobalSdsRevisionFactory(
            substance=substance, source_hash="n" * 64,
        )
        usage = SdsUsageFactory(
            sds_revision=old_rev,
            status=SdsUsageStatus.ACTIVE,
            approved_by=user,
            pending_update_revision=new_rev,
        )

        svc = SdsUsageService()
        new_usage = svc.adopt_update(usage, user)

        # New usage created with new revision
        assert new_usage.sds_revision == new_rev
        assert new_usage.status == SdsUsageStatus.ACTIVE
        assert new_usage.approved_by == user
        assert new_usage.tenant_id == usage.tenant_id

        # Old usage superseded
        usage.refresh_from_db()
        assert usage.status == SdsUsageStatus.SUPERSEDED

    def test_should_reject_adopt_without_pending_update(self, db, user):
        usage = SdsUsageFactory(
            status=SdsUsageStatus.ACTIVE,
            approved_by=user,
            pending_update_revision=None,
        )

        svc = SdsUsageService()
        with pytest.raises(ValueError, match="Kein pending Update"):
            svc.adopt_update(usage, user)


class TestDeferUpdate:
    """defer_update() — Zurückstellung mit Pflichtbegründung (GefStoffV §7)."""

    def test_should_defer_with_reason(self, db, user):
        substance = GlobalSubstanceFactory()
        new_rev = GlobalSdsRevisionFactory(
            substance=substance, source_hash="n" * 64,
        )
        usage = SdsUsageFactory(
            status=SdsUsageStatus.REVIEW_REQUIRED,
            approved_by=user,
            pending_update_revision=new_rev,
        )

        svc = SdsUsageService()
        deferred_until = date(2025, 12, 31)
        result = svc.defer_update(
            usage, user,
            reason="Laufende GBU muss erst abgeschlossen werden",
            deferred_until=deferred_until,
        )

        result.refresh_from_db()
        assert result.update_deferred_reason == "Laufende GBU muss erst abgeschlossen werden"
        assert result.update_deferred_until == deferred_until
        assert result.update_deferred_by == user

    def test_should_reject_defer_without_reason_gefstoffv_7(self, db, user):
        """GefStoffV §7: Reason is mandatory."""
        usage = SdsUsageFactory(
            status=SdsUsageStatus.REVIEW_REQUIRED,
            approved_by=user,
        )

        svc = SdsUsageService()
        with pytest.raises(ValueError, match="Pflichtbegründung"):
            svc.defer_update(usage, user, reason="")

    def test_should_reject_defer_with_whitespace_only_reason(self, db, user):
        """Whitespace-only reason should also be rejected."""
        usage = SdsUsageFactory(
            status=SdsUsageStatus.REVIEW_REQUIRED,
            approved_by=user,
        )

        svc = SdsUsageService()
        with pytest.raises(ValueError, match="Pflichtbegründung"):
            svc.defer_update(usage, user, reason="   ")

    def test_should_defer_without_deadline(self, db, user):
        """Deferral without specific deadline is allowed."""
        substance = GlobalSubstanceFactory()
        new_rev = GlobalSdsRevisionFactory(
            substance=substance, source_hash="n" * 64,
        )
        usage = SdsUsageFactory(
            status=SdsUsageStatus.REVIEW_REQUIRED,
            approved_by=user,
            pending_update_revision=new_rev,
        )

        svc = SdsUsageService()
        result = svc.defer_update(
            usage, user,
            reason="Betriebsferien bis Februar",
            deferred_until=None,
        )

        result.refresh_from_db()
        assert result.update_deferred_until is None
        assert result.update_deferred_reason == "Betriebsferien bis Februar"
