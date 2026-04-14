"""Tests for riskfw.substances — lookup, alias resolution, fuzzy matching."""

import pytest

from riskfw.exceptions import SubstanceNotFoundError
from riskfw.substances.database import SUBSTANCE_DATABASE, SubstanceProperties
from riskfw.substances.lookup import fuzzy_lookup, get_substance_properties, list_substances


@pytest.mark.unit
class TestGetSubstanceProperties:
    """get_substance_properties tests."""

    def test_should_find_by_exact_name(self):
        result = get_substance_properties("aceton")
        assert result.name == "Aceton"
        assert result.cas_number == "67-64-1"
        assert result.lower_explosion_limit == 2.5

    def test_should_resolve_english_alias(self):
        result = get_substance_properties("acetone")
        assert result.name == "Aceton"

    def test_should_resolve_gasoline_alias(self):
        result = get_substance_properties("gasoline")
        assert result.name == "Benzin (Ottokraftstoff)"

    def test_should_resolve_hydrogen_alias(self):
        result = get_substance_properties("hydrogen")
        assert result.name == "Wasserstoff"

    def test_should_be_case_insensitive(self):
        result = get_substance_properties("ETHANOL")
        assert result.name == "Ethanol"

    def test_should_strip_whitespace(self):
        result = get_substance_properties("  methanol  ")
        assert result.name == "Methanol"

    def test_should_fuzzy_match_close_name(self):
        result = get_substance_properties("acton")  # typo
        assert result.name == "Aceton"

    def test_should_raise_for_unknown_substance(self):
        with pytest.raises(SubstanceNotFoundError, match="not found"):
            get_substance_properties("unobtanium_xyz_999")

    def test_should_return_correct_temperature_class(self):
        result = get_substance_properties("benzin")
        assert result.temperature_class == "T3"

    def test_should_return_correct_explosion_group(self):
        result = get_substance_properties("wasserstoff")
        assert result.explosion_group == "IIC"


@pytest.mark.unit
class TestFuzzyLookup:
    """fuzzy_lookup tests."""

    def test_should_find_close_match(self):
        result = fuzzy_lookup("etanol")
        assert result == "ethanol"

    def test_should_return_none_for_no_match(self):
        result = fuzzy_lookup("completely_unknown_xyz")
        assert result is None

    def test_should_respect_threshold(self):
        result = fuzzy_lookup("act", threshold=0.9)
        assert result is None  # too strict for short partial match


@pytest.mark.unit
class TestListSubstances:
    """list_substances tests."""

    def test_should_return_all_substances(self):
        result = list_substances()
        assert len(result) == len(SUBSTANCE_DATABASE)
        assert all(isinstance(s, SubstanceProperties) for s in result)

    def test_should_include_known_substances(self):
        names = [s.name for s in list_substances()]
        assert "Aceton" in names
        assert "Wasserstoff" in names
        assert "Ethanol" in names
