# src/global_sds/tests/test_enrichment_service.py
"""Tests for SdsEnrichmentService (REFLEX web enrichment)."""

from unittest.mock import MagicMock, patch

from global_sds.services.enrichment_service import (
    EnrichmentResult,
    SdsEnrichmentService,
)


class TestEnrichmentService:
    """Unit tests — no network calls."""

    def test_should_return_empty_when_no_data(self):
        service = SdsEnrichmentService()
        result = service.enrich({})
        assert result.enriched is False
        assert result.cas_number == ""

    def test_should_return_empty_when_no_cas_and_no_name(self):
        service = SdsEnrichmentService()
        result = service.enrich({"cas_number": "", "product_name": ""})
        assert result.enriched is False

    @patch("global_sds.services.enrichment_service.SdsEnrichmentService._get_pubchem")
    def test_should_enrich_by_name(self, mock_get_pubchem):
        mock_sds = MagicMock()
        mock_sds.cas_number = "67-64-1"
        mock_sds.h_statements = ["H225", "H319"]
        mock_sds.p_statements = ["P210"]
        mock_sds.signal_word = "Danger"
        mock_sds.ghs_pictograms = ["GHS02"]
        mock_sds.substance_name = "propan-2-one"

        adapter = MagicMock()
        adapter.lookup_by_name.return_value = mock_sds
        mock_get_pubchem.return_value = adapter

        service = SdsEnrichmentService()
        result = service.enrich({
            "product_name": "Acetone",
            "cas_number": "",
        })

        assert result.enriched is True
        assert result.cas_number == "67-64-1"
        assert "H225" in result.h_statements
        assert result.signal_word == "Danger"
        assert result.source == "pubchem"
        adapter.lookup_by_name.assert_called_once_with("Acetone")

    @patch("global_sds.services.enrichment_service.SdsEnrichmentService._get_pubchem")
    def test_should_enrich_by_cas(self, mock_get_pubchem):
        mock_sds = MagicMock()
        mock_sds.cas_number = "64-17-5"
        mock_sds.h_statements = ["H225"]
        mock_sds.p_statements = []
        mock_sds.signal_word = "Danger"
        mock_sds.ghs_pictograms = []
        mock_sds.substance_name = "ethanol"

        adapter = MagicMock()
        adapter.lookup_by_cas.return_value = mock_sds
        mock_get_pubchem.return_value = adapter

        service = SdsEnrichmentService()
        result = service.enrich({
            "product_name": "Ethanol",
            "cas_number": "64-17-5",
        })

        assert result.enriched is True
        adapter.lookup_by_cas.assert_called_once_with("64-17-5")

    @patch("global_sds.services.enrichment_service.SdsEnrichmentService._get_pubchem")
    def test_should_handle_pubchem_failure(self, mock_get_pubchem):
        adapter = MagicMock()
        adapter.lookup_by_name.side_effect = Exception("timeout")
        mock_get_pubchem.return_value = adapter

        service = SdsEnrichmentService()
        result = service.enrich({"product_name": "Acetone"})

        assert result.enriched is False
        assert "PubChem: timeout" in result.errors

    @patch("global_sds.services.enrichment_service.SdsEnrichmentService._get_pubchem")
    def test_should_handle_no_result(self, mock_get_pubchem):
        adapter = MagicMock()
        adapter.lookup_by_name.return_value = None
        mock_get_pubchem.return_value = adapter

        service = SdsEnrichmentService()
        result = service.enrich({"product_name": "Unknown"})

        assert result.enriched is False

    def test_should_handle_reflex_not_installed(self):
        service = SdsEnrichmentService()
        service._pubchem = None
        # Force ImportError by patching
        with patch.dict("sys.modules", {"reflex.web": None}):
            pubchem = service._get_pubchem()
            assert pubchem is None


class TestMergeIntoParseResult:
    """Tests for merge_into_parse_result."""

    def test_should_fill_empty_cas(self):
        service = SdsEnrichmentService()
        result = service.merge_into_parse_result(
            {"cas_number": "", "h_statements": []},
            EnrichmentResult(
                enriched=True,
                cas_number="67-64-1",
                source="pubchem",
            ),
        )
        assert result["cas_number"] == "67-64-1"

    def test_should_not_overwrite_existing_cas(self):
        service = SdsEnrichmentService()
        result = service.merge_into_parse_result(
            {"cas_number": "64-17-5"},
            EnrichmentResult(
                enriched=True,
                cas_number="999-99-9",
                source="pubchem",
            ),
        )
        assert result["cas_number"] == "64-17-5"

    def test_should_merge_h_statements(self):
        service = SdsEnrichmentService()
        result = service.merge_into_parse_result(
            {"h_statements": ["H225"]},
            EnrichmentResult(
                enriched=True,
                h_statements=["H225", "H319", "H336"],
                source="pubchem",
            ),
        )
        assert result["h_statements"] == ["H225", "H319", "H336"]

    def test_should_fill_signal_word_when_none(self):
        service = SdsEnrichmentService()
        result = service.merge_into_parse_result(
            {"signal_word": "none"},
            EnrichmentResult(
                enriched=True,
                signal_word="Danger",
                source="pubchem",
            ),
        )
        assert result["signal_word"] == "danger"

    def test_should_not_overwrite_existing_signal_word(self):
        service = SdsEnrichmentService()
        result = service.merge_into_parse_result(
            {"signal_word": "warning"},
            EnrichmentResult(
                enriched=True,
                signal_word="Danger",
                source="pubchem",
            ),
        )
        assert result["signal_word"] == "warning"

    def test_should_return_unchanged_when_not_enriched(self):
        service = SdsEnrichmentService()
        original = {"cas_number": "", "h_statements": []}
        result = service.merge_into_parse_result(
            original,
            EnrichmentResult(enriched=False),
        )
        assert result == original
