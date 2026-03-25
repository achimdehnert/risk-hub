# src/explosionsschutz/tests/test_zone_classification.py
"""
Tests für die ZoneClassificationEngine (TRGS 721 Regelmatrix).

Keine DB erforderlich — reine Unit-Tests.
"""
import pytest

from explosionsschutz.services.zone_classification import (
    ZoneClassificationEngine,
    ZoneProposal,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def engine():
    return ZoneClassificationEngine()


class TestGasZoneClassification:
    """Gas-Zonen nach TRGS 721."""

    def test_should_return_zone_0_for_continuous_no_ventilation(self, engine):
        result = engine.propose("continuous", "none", "gas")
        assert result.zone_type == "0"
        assert result.confidence == "high"

    def test_should_return_zone_0_for_continuous_natural_ventilation(self, engine):
        result = engine.propose("continuous", "natural", "gas")
        assert result.zone_type == "0"
        assert result.confidence == "high"

    def test_should_return_zone_1_for_continuous_technical_dilution(self, engine):
        result = engine.propose("continuous", "technical_dilution", "gas")
        assert result.zone_type == "1"
        assert result.confidence == "medium"
        assert result.ventilation_reduction is True

    def test_should_return_no_zone_for_continuous_inertization(self, engine):
        result = engine.propose("continuous", "inertization", "gas")
        assert result.zone_type == "none"
        assert result.confidence == "high"

    def test_should_return_zone_1_for_primary_no_ventilation(self, engine):
        result = engine.propose("primary", "none", "gas")
        assert result.zone_type == "1"
        assert result.confidence == "high"

    def test_should_return_zone_1_for_primary_natural_ventilation(self, engine):
        result = engine.propose("primary", "natural", "gas")
        assert result.zone_type == "1"
        assert result.confidence == "high"

    def test_should_return_zone_2_for_primary_technical_dilution(self, engine):
        result = engine.propose("primary", "technical_dilution", "gas")
        assert result.zone_type == "2"
        assert result.confidence == "high"
        assert result.ventilation_reduction is True

    def test_should_return_zone_2_for_primary_local_exhaust(self, engine):
        result = engine.propose("primary", "local_exhaust", "gas")
        assert result.zone_type == "2"
        assert result.confidence == "medium"

    def test_should_return_no_zone_for_primary_inertization(self, engine):
        result = engine.propose("primary", "inertization", "gas")
        assert result.zone_type == "none"

    def test_should_return_zone_2_for_secondary_no_ventilation(self, engine):
        result = engine.propose("secondary", "none", "gas")
        assert result.zone_type == "2"
        assert result.confidence == "high"

    def test_should_return_zone_2_for_secondary_natural_ventilation(self, engine):
        result = engine.propose("secondary", "natural", "gas")
        assert result.zone_type == "2"

    def test_should_return_no_zone_for_secondary_technical_dilution(self, engine):
        result = engine.propose("secondary", "technical_dilution", "gas")
        assert result.zone_type == "none"
        assert result.ventilation_reduction is True

    def test_should_return_no_zone_for_secondary_local_exhaust(self, engine):
        result = engine.propose("secondary", "local_exhaust", "gas")
        assert result.zone_type == "none"

    def test_should_return_no_zone_for_secondary_inertization(self, engine):
        result = engine.propose("secondary", "inertization", "gas")
        assert result.zone_type == "none"
        assert result.confidence == "high"

    def test_should_always_eliminate_zone_with_inertization(self, engine):
        for grade in ("continuous", "primary", "secondary"):
            result = engine.propose(grade, "inertization", "gas")
            assert result.zone_type == "none", (
                f"Expected no zone for {grade}+inertization, got {result.zone_type}"
            )


class TestDustZoneClassification:
    """Staub-Zonen nach TRGS 746."""

    def test_should_return_zone_20_for_continuous_no_ventilation(self, engine):
        result = engine.propose("continuous", "none", "dust")
        assert result.zone_type == "20"
        assert result.confidence == "high"

    def test_should_return_zone_21_for_primary_no_ventilation(self, engine):
        result = engine.propose("primary", "none", "dust")
        assert result.zone_type == "21"

    def test_should_return_zone_22_for_primary_technical_dilution(self, engine):
        result = engine.propose("primary", "technical_dilution", "dust")
        assert result.zone_type == "22"
        assert result.ventilation_reduction is True

    def test_should_return_zone_22_for_secondary_no_ventilation(self, engine):
        result = engine.propose("secondary", "none", "dust")
        assert result.zone_type == "22"

    def test_should_return_no_zone_for_secondary_technical_dilution(self, engine):
        result = engine.propose("secondary", "technical_dilution", "dust")
        assert result.zone_type == "none"


class TestFallbackBehavior:
    """Konservativer Fallback bei unbekannten Kombinationen."""

    def test_should_return_low_confidence_for_unknown_gas_combo(self, engine):
        result = engine.propose("primary", "unknown_type", "gas")
        assert result.confidence == "low"
        assert result.zone_type == "1"

    def test_should_return_low_confidence_for_unknown_dust_combo(self, engine):
        result = engine.propose("primary", "unknown_type", "dust")
        assert result.confidence == "low"
        assert result.zone_type == "21"

    def test_should_include_trgs_reference_in_fallback(self, engine):
        result = engine.propose("unknown_grade", "none", "gas")
        assert "TRGS" in result.trgs_reference


class TestEquipmentCategoryMapping:
    """Mindest-ATEX-Kategorie pro Zone."""

    def test_should_return_1g_for_zone_0(self, engine):
        assert engine.get_required_equipment_category("0") == "1G"

    def test_should_return_2g_for_zone_1(self, engine):
        assert engine.get_required_equipment_category("1") == "2G"

    def test_should_return_3g_for_zone_2(self, engine):
        assert engine.get_required_equipment_category("2") == "3G"

    def test_should_return_1d_for_zone_20(self, engine):
        assert engine.get_required_equipment_category("20") == "1D"

    def test_should_return_2d_for_zone_21(self, engine):
        assert engine.get_required_equipment_category("21") == "2D"

    def test_should_return_3d_for_zone_22(self, engine):
        assert engine.get_required_equipment_category("22") == "3D"

    def test_should_return_dash_for_no_zone(self, engine):
        assert engine.get_required_equipment_category("none") == "—"

    def test_should_return_dash_for_unknown_zone(self, engine):
        assert engine.get_required_equipment_category("unknown") == "—"


class TestZoneProposalDataclass:
    """ZoneProposal ist immutable (frozen)."""

    def test_should_be_frozen(self):
        proposal = ZoneProposal(
            zone_type="2",
            confidence="high",
            justification="Test",
            trgs_reference="TRGS 721",
        )
        with pytest.raises(AttributeError):
            proposal.zone_type = "1"

    def test_should_have_default_ventilation_reduction_false(self):
        proposal = ZoneProposal(
            zone_type="1",
            confidence="high",
            justification="Test",
            trgs_reference="TRGS 721",
        )
        assert proposal.ventilation_reduction is False

    def test_should_include_all_required_fields(self):
        result = ZoneClassificationEngine().propose("primary", "none", "gas")
        assert result.zone_type
        assert result.confidence in ("high", "medium", "low")
        assert result.justification
        assert result.trgs_reference
