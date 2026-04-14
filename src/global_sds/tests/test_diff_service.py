# src/global_sds/tests/test_diff_service.py
"""Tests for SdsRevisionDiffService (ADR-012 §6)."""

import pytest

from global_sds.models import ImpactLevel, SdsRevisionDiffRecord
from global_sds.services.diff_service import SdsRevisionDiffService
from global_sds.tests.factories import GlobalSdsRevisionFactory, GlobalSubstanceFactory

pytestmark = pytest.mark.django_db


class TestFieldDiffs:
    """Detect field-level changes and classify impact."""

    def test_should_detect_safety_critical_flash_point_change(self, db):
        substance = GlobalSubstanceFactory()
        old = GlobalSdsRevisionFactory(
            substance=substance,
            flash_point_c=-20,
            source_hash="o" * 64,
        )
        new = GlobalSdsRevisionFactory(
            substance=substance,
            flash_point_c=-10,
            source_hash="n" * 64,
        )
        svc = SdsRevisionDiffService()
        result = svc.compute_diff(old, new)

        flash_diff = [d for d in result.field_diffs if d.field_name == "flash_point_c"]
        assert len(flash_diff) == 1
        assert flash_diff[0].impact == ImpactLevel.SAFETY_CRITICAL

    def test_should_detect_regulatory_wgk_change(self, db):
        substance = GlobalSubstanceFactory()
        old = GlobalSdsRevisionFactory(
            substance=substance,
            wgk=1,
            source_hash="o" * 64,
        )
        new = GlobalSdsRevisionFactory(
            substance=substance,
            wgk=3,
            source_hash="n" * 64,
        )
        svc = SdsRevisionDiffService()
        result = svc.compute_diff(old, new)

        wgk_diff = [d for d in result.field_diffs if d.field_name == "wgk"]
        assert len(wgk_diff) == 1
        assert wgk_diff[0].impact == ImpactLevel.REGULATORY

    def test_should_detect_informational_manufacturer_change(self, db):
        substance = GlobalSubstanceFactory()
        old = GlobalSdsRevisionFactory(
            substance=substance,
            manufacturer_name="Old GmbH",
            source_hash="o" * 64,
        )
        new = GlobalSdsRevisionFactory(
            substance=substance,
            manufacturer_name="New GmbH",
            source_hash="n" * 64,
        )
        svc = SdsRevisionDiffService()
        result = svc.compute_diff(old, new)

        mfr_diff = [d for d in result.field_diffs if d.field_name == "manufacturer_name"]
        assert len(mfr_diff) == 1
        assert mfr_diff[0].impact == ImpactLevel.INFORMATIONAL

    def test_should_report_no_changes_for_identical_revisions(self, db):
        substance = GlobalSubstanceFactory()
        old = GlobalSdsRevisionFactory(
            substance=substance,
            flash_point_c=-20,
            wgk=1,
            source_hash="o" * 64,
        )
        new = GlobalSdsRevisionFactory(
            substance=substance,
            flash_point_c=-20,
            wgk=1,
            source_hash="n" * 64,
            manufacturer_name=old.manufacturer_name,
            version_number=old.version_number,
            parse_confidence=old.parse_confidence,
            signal_word=old.signal_word,
            storage_class_trgs510=old.storage_class_trgs510,
            voc_percent=old.voc_percent,
            voc_g_per_l=old.voc_g_per_l,
            ignition_temperature_c=old.ignition_temperature_c,
            lower_explosion_limit=old.lower_explosion_limit,
            upper_explosion_limit=old.upper_explosion_limit,
        )
        svc = SdsRevisionDiffService()
        result = svc.compute_diff(old, new)
        # Only H-code diffs possible (both have no H-codes → no diff)
        scalar_diffs = [d for d in result.field_diffs if d.field_name != "hazard_statements"]
        assert len(scalar_diffs) == 0


class TestOverallImpact:
    """Overall impact = highest individual impact."""

    def test_should_compute_overall_as_safety_critical(self, db):
        substance = GlobalSubstanceFactory()
        old = GlobalSdsRevisionFactory(
            substance=substance,
            flash_point_c=-20,
            wgk=1,
            source_hash="o" * 64,
        )
        new = GlobalSdsRevisionFactory(
            substance=substance,
            flash_point_c=-10,
            wgk=2,
            source_hash="n" * 64,
        )
        svc = SdsRevisionDiffService()
        result = svc.compute_diff(old, new)
        assert result.overall_impact == ImpactLevel.SAFETY_CRITICAL

    def test_should_default_to_informational_when_no_diffs(self, db):
        from global_sds.services.diff_service import DiffResult

        result = DiffResult()
        assert result.overall_impact == ImpactLevel.INFORMATIONAL


class TestPersistDiff:
    """DiffRecord persistence."""

    def test_should_persist_diff_record(self, db):
        substance = GlobalSubstanceFactory()
        old = GlobalSdsRevisionFactory(
            substance=substance,
            flash_point_c=-20,
            source_hash="o" * 64,
        )
        new = GlobalSdsRevisionFactory(
            substance=substance,
            flash_point_c=-10,
            source_hash="n" * 64,
        )
        svc = SdsRevisionDiffService()
        diff = svc.compute_diff(old, new)
        record = svc.persist_diff(old, new, diff)

        assert record.pk is not None
        assert record.old_revision == old
        assert record.new_revision == new
        assert record.overall_impact == ImpactLevel.SAFETY_CRITICAL
        assert SdsRevisionDiffRecord.objects.count() == 1

    def test_should_be_idempotent_on_second_persist(self, db):
        substance = GlobalSubstanceFactory()
        old = GlobalSdsRevisionFactory(
            substance=substance,
            source_hash="o" * 64,
        )
        new = GlobalSdsRevisionFactory(
            substance=substance,
            source_hash="n" * 64,
        )
        svc = SdsRevisionDiffService()
        diff = svc.compute_diff(old, new)

        record1 = svc.persist_diff(old, new, diff)
        record2 = svc.persist_diff(old, new, diff)
        assert record1.pk == record2.pk
        assert SdsRevisionDiffRecord.objects.count() == 1
