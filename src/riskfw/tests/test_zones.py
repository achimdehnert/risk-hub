"""Tests for riskfw.zones — zone calculation and ventilation (TRGS 721/722)."""

import pytest

from riskfw.exceptions import ZoneCalculationError
from riskfw.zones.calculator import calculate_zone_extent
from riskfw.zones.models import ReleaseType, VentilationEffectiveness, ZoneType
from riskfw.zones.ventilation import analyze_ventilation_effectiveness


@pytest.mark.unit
class TestCalculateZoneExtent:
    """calculate_zone_extent per TRGS 721."""

    def test_should_return_zone_2_for_high_ventilation(self):
        result = calculate_zone_extent(
            release_rate_kg_s=0.001,
            ventilation_rate_m3_s=10.0,
            release_type="jet",
            lel_percent=2.5,
        )
        assert result.zone_type == ZoneType.ZONE_2
        assert result.dilution_factor >= 1000
        assert result.release_type == ReleaseType.JET
        assert result.basis_norm == "TRGS 721:2017-09"

    def test_should_return_zone_1_for_medium_ventilation(self):
        result = calculate_zone_extent(
            release_rate_kg_s=0.01,
            ventilation_rate_m3_s=5.0,
            release_type="pool",
            lel_percent=2.5,
        )
        assert result.zone_type == ZoneType.ZONE_1
        assert 100 <= result.dilution_factor < 1000

    def test_should_return_zone_0_for_low_ventilation(self):
        result = calculate_zone_extent(
            release_rate_kg_s=1.0,
            ventilation_rate_m3_s=10.0,
            release_type="diffuse",
            lel_percent=2.5,
        )
        assert result.zone_type == ZoneType.ZONE_0

    def test_should_return_zone_0_without_ventilation(self):
        result = calculate_zone_extent(
            release_rate_kg_s=0.01,
            ventilation_rate_m3_s=0.0,
            release_type="jet",
            lel_percent=2.5,
            room_volume_m3=100.0,
        )
        assert result.zone_type == ZoneType.ZONE_0
        assert len(result.warnings) > 0
        assert "Zone 0" in result.warnings[0]

    def test_should_warn_when_zone_exceeds_room(self):
        result = calculate_zone_extent(
            release_rate_kg_s=1.0,
            ventilation_rate_m3_s=0.5,
            release_type="jet",
            lel_percent=1.0,
            room_volume_m3=10.0,
        )
        assert any("exceeds room volume" in w for w in result.warnings)

    def test_should_use_substance_lel_lookup(self):
        result = calculate_zone_extent(
            release_rate_kg_s=0.001,
            ventilation_rate_m3_s=10.0,
            release_type="jet",
            substance_name="aceton",
        )
        assert result.lel_percent == 2.5

    def test_should_apply_correct_safety_factor(self):
        result_jet = calculate_zone_extent(
            release_rate_kg_s=0.01, ventilation_rate_m3_s=5.0,
            release_type="jet", lel_percent=2.5,
        )
        result_pool = calculate_zone_extent(
            release_rate_kg_s=0.01, ventilation_rate_m3_s=5.0,
            release_type="pool", lel_percent=2.5,
        )
        assert result_jet.safety_factor == 5.0
        assert result_pool.safety_factor == 3.0

    def test_should_reject_negative_release_rate(self):
        with pytest.raises(ZoneCalculationError, match="release_rate_kg_s"):
            calculate_zone_extent(
                release_rate_kg_s=-1.0,
                ventilation_rate_m3_s=1.0,
            )

    def test_should_reject_negative_ventilation_rate(self):
        with pytest.raises(ZoneCalculationError, match="ventilation_rate_m3_s"):
            calculate_zone_extent(
                release_rate_kg_s=0.01,
                ventilation_rate_m3_s=-1.0,
            )

    def test_should_reject_invalid_release_type(self):
        with pytest.raises(ZoneCalculationError, match="Unknown release_type"):
            calculate_zone_extent(
                release_rate_kg_s=0.01,
                ventilation_rate_m3_s=1.0,
                release_type="explosion",
            )

    def test_should_reject_zero_lel(self):
        with pytest.raises(ZoneCalculationError, match="lel_percent"):
            calculate_zone_extent(
                release_rate_kg_s=0.01,
                ventilation_rate_m3_s=1.0,
                lel_percent=0.0,
            )

    def test_should_return_positive_radius(self):
        result = calculate_zone_extent(
            release_rate_kg_s=0.01,
            ventilation_rate_m3_s=5.0,
            release_type="jet",
            lel_percent=2.5,
        )
        assert result.radius_m > 0
        assert result.volume_m3 > 0


@pytest.mark.unit
class TestAnalyzeVentilationEffectiveness:
    """analyze_ventilation_effectiveness per TRGS 722."""

    def test_should_classify_high_technical_ventilation(self):
        result = analyze_ventilation_effectiveness(
            room_volume_m3=100.0,
            air_flow_m3_h=1200.0,
            ventilation_type="technisch",
        )
        assert result.effectiveness == VentilationEffectiveness.HIGH
        assert result.can_reduce_zone is True
        assert result.air_changes_per_hour == 12.0

    def test_should_classify_medium_technical_ventilation(self):
        result = analyze_ventilation_effectiveness(
            room_volume_m3=100.0,
            air_flow_m3_h=800.0,
            ventilation_type="technisch",
        )
        assert result.effectiveness == VentilationEffectiveness.MEDIUM
        assert result.can_reduce_zone is True  # has_ex_zone=True by default

    def test_should_classify_low_technical_ventilation(self):
        result = analyze_ventilation_effectiveness(
            room_volume_m3=100.0,
            air_flow_m3_h=400.0,
            ventilation_type="technisch",
        )
        assert result.effectiveness == VentilationEffectiveness.LOW
        assert result.can_reduce_zone is False

    def test_should_not_reduce_zone_for_natural_ventilation(self):
        result = analyze_ventilation_effectiveness(
            room_volume_m3=100.0,
            air_flow_m3_h=2000.0,
            ventilation_type="natuerlich",
        )
        assert result.effectiveness == VentilationEffectiveness.VARIABLE
        assert result.can_reduce_zone is False

    def test_should_flag_no_ventilation(self):
        result = analyze_ventilation_effectiveness(
            room_volume_m3=100.0,
            air_flow_m3_h=0.0,
            ventilation_type="keine",
        )
        assert result.effectiveness == VentilationEffectiveness.NONE
        assert result.can_reduce_zone is False

    def test_should_handle_zero_room_volume(self):
        result = analyze_ventilation_effectiveness(
            room_volume_m3=0.0,
            air_flow_m3_h=500.0,
        )
        assert result.air_changes_per_hour == 0.0

    def test_should_include_basis_norm(self):
        result = analyze_ventilation_effectiveness(
            room_volume_m3=100.0,
            air_flow_m3_h=1200.0,
        )
        assert result.basis_norm == "TRGS 722:2012-08"
