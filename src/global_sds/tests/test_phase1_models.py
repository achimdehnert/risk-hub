# global_sds/tests/test_phase1_models.py
"""Tests für Phase 1 Models: PropertyDefinition, RevisionProperty, Substance fields, DiffRecord properties, SdsUsage QuerySets."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from global_sds.models import (
    ImpactLevel,
    SdsPropertyDefinition,
    _normalize_cas,
)
from global_sds.sds_usage import SdsUsage, SdsUsageStatus
from global_sds.tests.factories import (
    GlobalSdsRevisionFactory,
    GlobalSubstanceFactory,
    SdsPropertyDefinitionFactory,
    SdsRevisionDiffRecordFactory,
    SdsRevisionPropertyFactory,
    SdsUsageFactory,
)

pytestmark = pytest.mark.django_db


# ── CAS Normalization ────────────────────────────────────────────────


class TestCasNormalization:
    def test_should_normalize_cas_with_dashes(self):
        assert _normalize_cas("111-76-2") == "111762"

    def test_should_normalize_cas_with_spaces(self):
        assert _normalize_cas(" 111 76 2 ") == "111762"

    def test_should_return_empty_for_none(self):
        assert _normalize_cas(None) == ""

    def test_should_return_empty_for_blank(self):
        assert _normalize_cas("") == ""

    def test_should_auto_set_normalized_on_save(self):
        s = GlobalSubstanceFactory(cas_number="111-76-2")
        assert s.cas_number_normalized == "111762"

    def test_should_set_empty_normalized_when_no_cas(self):
        s = GlobalSubstanceFactory(cas_number=None)
        assert s.cas_number_normalized == ""


# ── SdsPropertyDefinition ────────────────────────────────────────────


class TestSdsPropertyDefinition:
    def test_should_create_definition(self):
        defn = SdsPropertyDefinitionFactory(
            key="flash_point",
            label_de="Flammpunkt",
            value_type=SdsPropertyDefinition.ValueType.NUMERIC,
            unit="°C",
        )
        assert defn.pk is not None
        assert defn.key == "flash_point"
        assert str(defn) == "flash_point (Numerisch (Einzelwert))"

    def test_should_enforce_unique_key(self):
        SdsPropertyDefinitionFactory(key="density")
        with pytest.raises(Exception):
            SdsPropertyDefinitionFactory(key="density")


# ── SdsRevisionProperty ──────────────────────────────────────────────


class TestSdsRevisionProperty:
    def test_should_create_property_with_numeric_value(self):
        prop = SdsRevisionPropertyFactory(
            value_numeric_lo=Decimal("65.5"),
            confidence=0.92,
            parse_source="regex",
        )
        assert prop.pk is not None
        assert prop.value_numeric_lo == Decimal("65.5")
        assert prop.confidence == 0.92

    def test_should_enforce_unique_per_revision_definition(self):
        rev = GlobalSdsRevisionFactory()
        defn = SdsPropertyDefinitionFactory()
        SdsRevisionPropertyFactory(sds_revision=rev, definition=defn)
        with pytest.raises(Exception):
            SdsRevisionPropertyFactory(sds_revision=rev, definition=defn)

    def test_should_allow_text_value(self):
        prop = SdsRevisionPropertyFactory(
            value_numeric_lo=None,
            value_text="not soluble",
        )
        assert prop.value_text == "not soluble"

    def test_should_store_temperature_reference(self):
        prop = SdsRevisionPropertyFactory(
            temperature_c=Decimal("20.00"),
        )
        assert prop.temperature_c == Decimal("20.00")


# ── DiffRecord Properties ────────────────────────────────────────────


class TestDiffRecordProperties:
    def test_should_require_gbu_review_when_safety_critical(self):
        diff = SdsRevisionDiffRecordFactory(
            overall_impact=ImpactLevel.SAFETY_CRITICAL,
        )
        assert diff.requires_gbu_review is True

    def test_should_require_gbu_review_when_h_codes_added(self):
        diff = SdsRevisionDiffRecordFactory(
            overall_impact=ImpactLevel.INFORMATIONAL,
            added_h_codes=["H301"],
        )
        assert diff.requires_gbu_review is True

    def test_should_not_require_gbu_review_when_informational(self):
        diff = SdsRevisionDiffRecordFactory(
            overall_impact=ImpactLevel.INFORMATIONAL,
            added_h_codes=[],
            removed_h_codes=[],
        )
        assert diff.requires_gbu_review is False

    def test_should_require_ex_review_when_flash_point_changed(self):
        diff = SdsRevisionDiffRecordFactory(
            overall_impact=ImpactLevel.REGULATORY,
            field_diffs=[{"field": "flash_point_c", "old": "65", "new": "55"}],
        )
        assert diff.requires_ex_review is True

    def test_should_not_require_ex_review_for_non_ex_fields(self):
        diff = SdsRevisionDiffRecordFactory(
            overall_impact=ImpactLevel.REGULATORY,
            field_diffs=[{"field": "wgk", "old": "1", "new": "2"}],
        )
        assert diff.requires_ex_review is False


# ── SdsUsage QuerySets ───────────────────────────────────────────────


class TestSdsUsageQuerySets:
    def test_should_filter_for_tenant(self):
        tid = uuid.uuid4()
        SdsUsageFactory(tenant_id=tid)
        SdsUsageFactory(tenant_id=uuid.uuid4())
        assert SdsUsage.objects.for_tenant(tid).count() == 1

    def test_should_find_requiring_action(self):
        tid = uuid.uuid4()
        SdsUsageFactory(tenant_id=tid, status=SdsUsageStatus.SUPERSEDED)
        SdsUsageFactory(tenant_id=tid, status=SdsUsageStatus.REVIEW_REQUIRED)
        SdsUsageFactory(tenant_id=tid, status=SdsUsageStatus.UPDATE_AVAILABLE)
        SdsUsageFactory(tenant_id=tid, status=SdsUsageStatus.PENDING_APPROVAL)
        assert SdsUsage.objects.for_tenant(tid).requiring_action().count() == 3

    def test_should_find_overdue(self):
        tid = uuid.uuid4()
        SdsUsageFactory(
            tenant_id=tid,
            status=SdsUsageStatus.REVIEW_REQUIRED,
            review_deadline=date.today() - timedelta(days=1),
        )
        SdsUsageFactory(
            tenant_id=tid,
            status=SdsUsageStatus.REVIEW_REQUIRED,
            review_deadline=date.today() + timedelta(days=30),
        )
        assert SdsUsage.objects.for_tenant(tid).overdue().count() == 1

    def test_should_find_with_pending_update(self):
        tid = uuid.uuid4()
        rev1 = GlobalSdsRevisionFactory()
        rev2 = GlobalSdsRevisionFactory()
        SdsUsageFactory(tenant_id=tid, sds_revision=rev1, pending_update_revision=rev2)
        SdsUsageFactory(tenant_id=tid)
        assert SdsUsage.objects.for_tenant(tid).with_pending_update().count() == 1

    def test_should_find_active_only(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        approver = User.objects.create_user(username="approver", password="test")
        tid = uuid.uuid4()
        SdsUsageFactory(
            tenant_id=tid,
            status=SdsUsageStatus.ACTIVE,
            approved_by=approver,
        )
        SdsUsageFactory(tenant_id=tid, status=SdsUsageStatus.SUPERSEDED)
        assert SdsUsage.objects.for_tenant(tid).active().count() == 1
