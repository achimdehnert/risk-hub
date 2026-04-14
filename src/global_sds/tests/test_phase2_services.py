# global_sds/tests/test_phase2_services.py
"""Tests für Phase 2 Service-Verbesserungen: DTO, Version-Parser, CAS-normalized lookup."""

from datetime import date

import pytest

from global_sds.services.dtos import ParsedSdsData
from global_sds.services.identity_resolver import SdsIdentityResolver
from global_sds.services.version_detector import SdsVersionDetector, VersionOutcome
from global_sds.tests.factories import GlobalSdsRevisionFactory, GlobalSubstanceFactory

pytestmark = pytest.mark.django_db


# ── ParsedSdsData DTO ────────────────────────────────────────────────


class TestParsedSdsData:
    def test_should_be_frozen(self):
        data = ParsedSdsData(product_name="Aceton")
        with pytest.raises(AttributeError):
            data.product_name = "changed"

    def test_should_convert_to_dict(self):
        data = ParsedSdsData(
            product_name="Aceton",
            cas_number="67-64-1",
            revision_date=date(2025, 6, 1),
            flash_point_c=-20.0,
            h_codes=("H225", "H319"),
            parse_confidence=0.92,
        )
        d = data.to_dict()
        assert d["product_name"] == "Aceton"
        assert d["revision_date"] == "2025-06-01"
        assert d["h_codes"] == ["H225", "H319"]
        assert d["flash_point_c"] == -20.0
        assert "manufacturer_name" not in d  # empty string excluded

    def test_should_have_defaults(self):
        data = ParsedSdsData()
        assert data.product_name == ""
        assert data.revision_date is None
        assert data.h_codes == ()
        assert data.parse_confidence == 0.0


# ── VersionDetector robust parsing ───────────────────────────────────


class TestVersionParserRobust:
    def test_should_parse_simple_version(self):
        detector = SdsVersionDetector()
        assert detector._parse_version("4") == (4,)

    def test_should_parse_dotted_version(self):
        detector = SdsVersionDetector()
        assert detector._parse_version("1.2.3") == (1, 2, 3)

    def test_should_handle_suffix_letters(self):
        detector = SdsVersionDetector()
        assert detector._parse_version("3a") == (3,)
        assert detector._parse_version("1.2b") == (1, 2)

    def test_should_handle_dash_suffix(self):
        detector = SdsVersionDetector()
        assert detector._parse_version("2.1-beta") == (2, 1)

    def test_should_raise_for_non_numeric(self):
        detector = SdsVersionDetector()
        with pytest.raises(ValueError):
            detector._parse_version("abc")

    def test_should_detect_new_revision_with_suffix_versions(self):
        substance = GlobalSubstanceFactory()
        GlobalSdsRevisionFactory(
            substance=substance,
            version_number="2a",
            revision_date=None,
        )
        detector = SdsVersionDetector()
        result = detector.detect(
            substance=substance,
            revision_date=None,
            version_number="3b",
        )
        assert result.outcome == VersionOutcome.NEW_REVISION


# ── IdentityResolver CAS normalized ─────────────────────────────────


class TestIdentityResolverCasNormalized:
    def test_should_match_cas_with_different_formatting(self):
        GlobalSubstanceFactory(cas_number="111-76-2")
        resolver = SdsIdentityResolver()
        result = resolver.resolve(
            cas_number="111 76 2",  # spaces instead of dashes
            product_name="irrelevant",
        )
        assert result.match_type == "cas_exact"
        assert result.confidence == 0.98

    def test_should_match_cas_without_dashes(self):
        GlobalSubstanceFactory(cas_number="67-64-1")
        resolver = SdsIdentityResolver()
        result = resolver.resolve(
            cas_number="67641",
            product_name="irrelevant",
        )
        assert result.match_type == "cas_exact"

    def test_should_return_none_for_empty_cas(self):
        resolver = SdsIdentityResolver()
        result = resolver.resolve(
            cas_number="",
            product_name="Unknown Product",
        )
        # Falls through to fuzzy (no substances → no match)
        assert result.match_type in ("fuzzy", "none")
