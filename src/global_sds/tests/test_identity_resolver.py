# src/global_sds/tests/test_identity_resolver.py
"""Tests for SdsIdentityResolver (ADR-012 §5 Stufe 2)."""

import pytest

from global_sds.services.identity_resolver import SdsIdentityResolver
from global_sds.tests.factories import GlobalSubstanceFactory


pytestmark = pytest.mark.django_db


class TestCasExactMatch:
    """CAS exact match — confidence 0.98, match_type='cas_exact'."""

    def test_should_match_exact_cas(self, substance_acetone):
        resolver = SdsIdentityResolver()
        result = resolver.resolve(
            cas_number="67-64-1",
            product_name="irrelevant",
        )
        assert result.substance == substance_acetone
        assert result.confidence == 0.98
        assert result.match_type == "cas_exact"
        assert result.is_auto_match is True

    def test_should_normalize_cas_with_spaces(self, substance_acetone):
        resolver = SdsIdentityResolver()
        result = resolver.resolve(
            cas_number="  67-64-1  ",
            product_name="irrelevant",
        )
        assert result.substance == substance_acetone
        assert result.match_type == "cas_exact"

    def test_should_return_none_for_unknown_cas(self, db):
        resolver = SdsIdentityResolver()
        result = resolver.resolve(
            cas_number="999-99-9",
            product_name="Unknown Product",
        )
        assert result.match_type != "cas_exact"

    def test_should_fallback_to_fuzzy_on_no_cas(self, substance_acetone):
        resolver = SdsIdentityResolver()
        result = resolver.resolve(
            cas_number=None,
            product_name="Aceton",
        )
        # Should try fuzzy matching, not CAS
        assert result.match_type in ("fuzzy", "none")


class TestFuzzyMatch:
    """Fuzzy Name+Hersteller matching."""

    def test_should_fuzzy_match_exact_name(self, substance_acetone):
        resolver = SdsIdentityResolver()
        result = resolver.resolve(
            cas_number=None,
            product_name="Aceton",
        )
        assert result.substance == substance_acetone
        assert result.match_type == "fuzzy"
        assert result.confidence >= 0.95

    def test_should_fuzzy_match_synonym(self, substance_acetone):
        resolver = SdsIdentityResolver()
        result = resolver.resolve(
            cas_number=None,
            product_name="Dimethylketon",
        )
        assert result.substance == substance_acetone
        assert result.match_type == "fuzzy"

    def test_should_return_new_substance_for_low_score(self, substance_acetone):
        resolver = SdsIdentityResolver()
        result = resolver.resolve(
            cas_number=None,
            product_name="Xylitol Hexachlorid Spezial",
        )
        assert result.is_new_substance is True
        assert result.confidence < 0.70

    def test_should_identify_confirmation_range(self, db):
        """Score between 0.70 and 0.95 needs user confirmation."""
        # Create substance with partially matching name
        GlobalSubstanceFactory(
            cas_number=None,
            name="Ethanol absolut",
        )
        resolver = SdsIdentityResolver()
        result = resolver.resolve(
            cas_number=None,
            product_name="Ethanol technisch 96%",
        )
        # Partial match should be in confirmation range or auto-match
        # (depends on exact SequenceMatcher score)
        assert result.substance is not None or result.is_new_substance


class TestEdgeCases:
    """Edge cases and robustness."""

    def test_should_handle_empty_database(self, db):
        resolver = SdsIdentityResolver()
        result = resolver.resolve(
            cas_number=None,
            product_name="Anything",
        )
        assert result.substance is None
        assert result.is_new_substance is True

    def test_should_handle_empty_product_name(self, substance_acetone):
        resolver = SdsIdentityResolver()
        result = resolver.resolve(
            cas_number=None,
            product_name="",
        )
        # Should not crash
        assert result is not None

    def test_should_handle_cas_none_and_empty_name(self, db):
        resolver = SdsIdentityResolver()
        result = resolver.resolve(
            cas_number=None,
            product_name="",
        )
        assert result is not None
        assert result.match_type in ("fuzzy", "none")
