"""Tests for SubstanceLookupService bridge to iil-enrichment."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from substances.services.substance_lookup import (
    LookupResult,
    SubstanceLookupService,
)


@pytest.fixture()
def svc():
    return SubstanceLookupService()


def _make_enrichment_result(props_dict: dict, source="GESTIS+PubChem"):
    """Build a mock EnrichmentResult with PropertyValue-like objects."""
    mock = MagicMock()
    mock.is_empty = False
    mock.source = source

    properties = {}
    for key, val in props_dict.items():
        pv = MagicMock()
        pv.value = val
        properties[key] = pv

    mock.properties = properties
    return mock


def _empty_result():
    mock = MagicMock()
    mock.is_empty = True
    mock.source = ""
    mock.properties = {}
    return mock


class TestLookupEmpty:
    def test_should_return_empty_for_blank_query(self, svc):
        result = svc.lookup("")
        assert result.found is False

    def test_should_return_empty_for_whitespace(self, svc):
        result = svc.lookup("   ")
        assert result.found is False

    def test_should_return_empty_if_enrichment_not_installed(self):
        """ImportError → empty result."""
        with patch.dict("sys.modules", {"enrichment": None}):
            with pytest.warns(UserWarning, match="iil-enrichment not installed"):
                # Re-import to trigger ImportError path
                import importlib  # noqa: I001

                import substances.services.substance_lookup as mod

                importlib.reload(mod)
                result = mod.SubstanceLookupService().lookup("test")
                assert result.found is False


class TestLookupMapping:
    @patch("enrichment.default_registry")
    def test_should_map_identity_fields(self, mock_registry, svc):
        mock_registry.enrich_merged.return_value = _make_enrichment_result({
            "name": "Aceton",
            "cas_number": "67-64-1",
            "ec_number": "200-662-2",
            "iupac_name": "propan-2-one",
            "molecular_formula": "C3H6O",
            "molecular_weight": "58.08",
            "pubchem_cid": 180,
            "gestis_zvg": "001140",
        })

        with patch(
            "substances.services.substance_lookup.default_registry",
            mock_registry,
        ):
            result = svc.lookup("67-64-1")

        assert result.found is True
        assert result.name == "Aceton"
        assert result.cas == "67-64-1"
        assert result.ec_number == "200-662-2"
        assert result.iupac_name == "propan-2-one"
        assert result.molecular_formula == "C3H6O"
        assert result.pubchem_cid == 180
        assert result.gestis_zvg == "001140"

    @patch("enrichment.default_registry")
    def test_should_map_ghs_fields(self, mock_registry, svc):
        mock_registry.enrich_merged.return_value = _make_enrichment_result({
            "h_statements": ["H225", "H319", "H336"],
            "p_statements": ["P210", "P233"],
            "signal_word": "danger",
            "pictograms": ["GHS02", "GHS07"],
            "ghs_einstufung": "Gefahr H225 H319",
            "is_cmr": False,
        })

        with patch(
            "substances.services.substance_lookup.default_registry",
            mock_registry,
        ):
            result = svc.lookup("67-64-1")

        assert result.signal_word == "danger"
        assert "H225" in result.h_statements
        assert "P210" in result.p_statements
        assert "GHS02" in result.pictograms
        assert result.is_cmr is False
        assert any("H225" in d for d in result.ghs_descriptions)

    @patch("enrichment.default_registry")
    def test_should_map_physical_properties(self, mock_registry, svc):
        mock_registry.enrich_merged.return_value = _make_enrichment_result({
            "flash_point_c": -20.0,
            "boiling_point_c": 56.2,
            "melting_point_c": -94.7,
            "density": 0.79,
            "ignition_temperature_c": 465.0,
            "temperature_class": "T1",
            "explosion_group": "IIA",
            "explosion_limits": "2.5 - 12.8 Vol%",
        })

        with patch(
            "substances.services.substance_lookup.default_registry",
            mock_registry,
        ):
            result = svc.lookup("67-64-1")

        assert result.flash_point == "-20.0 °C"
        assert result.boiling_point == "56.2 °C"
        assert result.melting_point == "-94.7 °C"
        assert result.density == "0.79 g/cm³"
        assert result.temp_class == "T1"
        assert result.explosion_group == "IIA"

    @patch("enrichment.default_registry")
    def test_should_return_empty_when_not_found(self, mock_registry, svc):
        mock_registry.enrich_merged.return_value = _empty_result()

        with patch(
            "substances.services.substance_lookup.default_registry",
            mock_registry,
        ):
            result = svc.lookup("unknown-substance-xyz")

        assert result.found is False


class TestToImportRecord:
    def test_should_convert_to_import_record(self):
        result = LookupResult(
            found=True,
            source="GESTIS",
            name="Aceton",
            cas="67-64-1",
            ec_number="200-662-2",
            signal_word="danger",
            h_statements=["H225", "H319"],
            p_statements=["P210"],
            flash_point="-20 °C",
            agw="500 ml/m³",
        )

        record = result.to_import_record()

        assert record["name"] == "Aceton"
        assert record["cas"] == "67-64-1"
        assert record["ec"] == "200-662-2"
        assert record["signal_word"] == "danger"
        assert record["flash_point_c"] == pytest.approx(-20.0)
        assert record["agw"] == "500 ml/m³"
        assert "H225" in record["h_statements"]

    def test_should_handle_empty_result(self):
        result = LookupResult()
        record = result.to_import_record()
        assert record["name"] == ""
        assert record["flash_point_c"] is None


class TestHCodeDescriptions:
    def test_should_map_known_codes(self):
        descs = SubstanceLookupService._h_codes_to_descriptions({"H225", "H319"})
        assert len(descs) == 2
        assert any("entzündbar" in d.lower() for d in descs)

    def test_should_skip_unknown_codes(self):
        descs = SubstanceLookupService._h_codes_to_descriptions({"H999"})
        assert len(descs) == 0

    def test_should_detect_cmr_codes(self):
        descs = SubstanceLookupService._h_codes_to_descriptions({"H350"})
        assert len(descs) == 1
        assert "Krebs" in descs[0]
