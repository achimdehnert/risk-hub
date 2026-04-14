"""Tests for riskfw.ignition — ignition source assessment per EN 1127-1:2019."""

import pytest

from riskfw.ignition.assessor import IGNITION_SOURCES, IgnitionSourceMatrix
from riskfw.ignition.models import IgnitionRisk


@pytest.mark.unit
class TestIgnitionSourceMatrix:
    """IgnitionSourceMatrix tests."""

    def test_should_assess_not_present_as_none_risk(self):
        matrix = IgnitionSourceMatrix()
        result = matrix.assess("S01", is_present=False, is_effective=False)
        assert result.risk_level == IgnitionRisk.NONE
        assert result.source_name == "Heisse Oberflaechen"

    def test_should_assess_present_effective_no_mitigation_as_high(self):
        matrix = IgnitionSourceMatrix()
        result = matrix.assess("S04", is_present=True, is_effective=True)
        assert result.risk_level == IgnitionRisk.HIGH

    def test_should_assess_present_effective_with_mitigation_as_low(self):
        matrix = IgnitionSourceMatrix()
        result = matrix.assess(
            "S06",
            is_present=True,
            is_effective=True,
            mitigation="Erdung installiert",
        )
        assert result.risk_level == IgnitionRisk.LOW

    def test_should_assess_present_not_effective_as_low(self):
        matrix = IgnitionSourceMatrix()
        result = matrix.assess("S02", is_present=True, is_effective=False)
        assert result.risk_level == IgnitionRisk.LOW

    def test_should_include_norm_reference(self):
        matrix = IgnitionSourceMatrix()
        result = matrix.assess("S01", is_present=False, is_effective=False)
        assert result.norm_reference == "EN 1127-1:2019"
        assert "6.1" in result.norm_clause

    def test_should_raise_for_unknown_source(self):
        matrix = IgnitionSourceMatrix()
        with pytest.raises(ValueError, match="Unknown ignition source"):
            matrix.assess("S99", is_present=True, is_effective=True)

    def test_should_have_13_sources(self):
        matrix = IgnitionSourceMatrix()
        assert len(matrix.all_sources) == 13

    def test_should_assess_all_in_batch(self):
        matrix = IgnitionSourceMatrix()
        assessments = [
            {"source_id": "S01", "is_present": True, "is_effective": False},
            {"source_id": "S02", "is_present": False, "is_effective": False},
            {"source_id": "S03", "is_present": True, "is_effective": True, "mitigation": "Funkenflug verhindert"},
        ]
        results = matrix.assess_all(assessments)
        assert len(results) == 3
        assert results[0].risk_level == IgnitionRisk.LOW
        assert results[1].risk_level == IgnitionRisk.NONE
        assert results[2].risk_level == IgnitionRisk.LOW

    def test_should_cover_all_13_source_ids(self):
        matrix = IgnitionSourceMatrix()
        for source_id in IGNITION_SOURCES:
            result = matrix.assess(source_id, is_present=False, is_effective=False)
            assert result.source_id == source_id
            assert result.risk_level == IgnitionRisk.NONE
