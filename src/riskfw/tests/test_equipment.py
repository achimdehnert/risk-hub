"""Tests for riskfw.equipment — ATEX equipment suitability check."""

import pytest

from riskfw.equipment.checker import check_equipment_suitability
from riskfw.exceptions import ATEXCheckError


@pytest.mark.unit
class TestCheckEquipmentSuitability:
    """check_equipment_suitability per ATEX 2014/34/EU."""

    def test_should_approve_1g_in_zone_0(self):
        result = check_equipment_suitability("II 1G Ex ia IIC T6", "0")
        assert result.is_suitable is True
        assert result.detected_category == "1G"
        assert result.detected_temp_class == "T6"
        assert result.detected_exp_group == "IIC"

    def test_should_approve_2g_in_zone_1(self):
        result = check_equipment_suitability("II 2G Ex d IIB T4", "1")
        assert result.is_suitable is True
        assert result.detected_category == "2G"

    def test_should_approve_1g_in_zone_1(self):
        """1G is always suitable for zones 0/1/2."""
        result = check_equipment_suitability("II 1G Ex ia IIC T6", "1")
        assert result.is_suitable is True

    def test_should_approve_3g_in_zone_2(self):
        result = check_equipment_suitability("II 3G Ex nA IIA T3", "2")
        assert result.is_suitable is True

    def test_should_reject_3g_in_zone_0(self):
        result = check_equipment_suitability("II 3G Ex nA IIA T3", "0")
        assert result.is_suitable is False
        assert len(result.issues) > 0

    def test_should_reject_3g_in_zone_1(self):
        result = check_equipment_suitability("II 3G Ex nA IIA T3", "1")
        assert result.is_suitable is False

    def test_should_reject_2g_in_zone_0(self):
        result = check_equipment_suitability("II 2G Ex d IIB T4", "0")
        assert result.is_suitable is False

    def test_should_handle_dust_zones(self):
        result = check_equipment_suitability("II 1D Ex tD IIIC T100", "20")
        assert result.is_suitable is True
        assert result.detected_category == "1D"

    def test_should_reject_3d_in_zone_20(self):
        result = check_equipment_suitability("II 3D Ex tc IIIA T200", "20")
        assert result.is_suitable is False

    def test_should_normalize_zone_string(self):
        result = check_equipment_suitability("II 2G Ex d IIB T4", "Zone 1")
        assert result.is_suitable is True
        assert result.target_zone == "1"

    def test_should_raise_for_unknown_zone(self):
        with pytest.raises(ATEXCheckError, match="Unknown zone"):
            check_equipment_suitability("II 2G Ex d IIB T4", "99")

    def test_should_flag_missing_category(self):
        result = check_equipment_suitability("Ex d IIB T4", "1")
        assert result.is_suitable is False
        assert result.detected_category is None
        assert any("Geraetekategorie" in i for i in result.issues)

    def test_should_flag_missing_temp_class(self):
        result = check_equipment_suitability("II 2G Ex d IIB", "1")
        assert result.is_suitable is False
        assert result.detected_temp_class is None

    def test_should_flag_missing_exp_group(self):
        result = check_equipment_suitability("II 2G Ex d T4", "1")
        assert result.is_suitable is False
        assert result.detected_exp_group is None

    def test_should_include_basis_norm(self):
        result = check_equipment_suitability("II 2G Ex d IIB T4", "1")
        assert result.basis_norm == "ATEX 2014/34/EU"
