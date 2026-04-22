# src/global_sds/tests/test_enrichment_service.py
"""Tests for SdsEnrichmentService (iil-enrichment ADR-169)."""

from unittest.mock import MagicMock, patch

from global_sds.services.enrichment_service import (
    SdsEnrichmentResult,
    SdsEnrichmentService,
)


def _make_enrichment_result(properties=None, source="GESTIS", confidence=0.8):
    """Build a mock enrichment.types.EnrichmentResult."""
    mock = MagicMock()
    mock.is_empty = not properties
    mock.source = source
    mock.properties = properties or {}
    mock.confidence = confidence

    def _get(key):
        return properties.get(key) if properties else None

    mock.get = _get
    return mock


def _make_property_value(value, value_type="text"):
    """Build a mock enrichment.types.PropertyValue."""
    mock = MagicMock()
    mock.value = value
    mock.value_type = value_type
    return mock


class TestEnrichmentService:
    """Unit tests — no network calls, mocks iil-enrichment registry."""

    def test_should_return_empty_when_no_data(self):
        service = SdsEnrichmentService()
        result = service.enrich({})
        assert result.enriched is False
        assert result.cas_number == ""

    def test_should_return_empty_when_no_cas_and_no_name(self):
        service = SdsEnrichmentService()
        result = service.enrich({"cas_number": "", "product_name": ""})
        assert result.enriched is False

    @patch("global_sds.services.enrichment_service.default_registry", create=True)
    def test_should_enrich_via_registry(self, mock_registry_import):
        props = {
            "h_statements": _make_property_value(["H225", "H319"], "list"),
            "p_statements": _make_property_value(["P210"], "list"),
            "signal_word": _make_property_value("danger", "text"),
            "pictograms": _make_property_value(["GHS02"], "list"),
            "iupac_name": _make_property_value("propan-2-one", "text"),
        }
        enriched = _make_enrichment_result(props, source="GESTIS,PubChem")

        with patch(
            "global_sds.services.enrichment_service.default_registry",
            create=True,
        ) as mock_reg:
            mock_reg.enrich_merged.return_value = enriched

            service = SdsEnrichmentService()
            result = service.enrich({"product_name": "Acetone", "cas_number": ""})

        assert result.enriched is True
        assert "H225" in result.h_statements
        assert result.signal_word == "danger"
        assert result.iupac_name == "propan-2-one"
        assert result.source == "GESTIS,PubChem"

    @patch("global_sds.services.enrichment_service.default_registry", create=True)
    def test_should_enrich_by_cas_as_natural_key(self, mock_registry_import):
        enriched = _make_enrichment_result(
            {"h_statements": _make_property_value(["H225"], "list")},
            source="GESTIS",
        )

        with patch(
            "global_sds.services.enrichment_service.default_registry",
            create=True,
        ) as mock_reg:
            mock_reg.enrich_merged.return_value = enriched

            service = SdsEnrichmentService()
            result = service.enrich(
                {"product_name": "Ethanol", "cas_number": "64-17-5"}
            )

        assert result.enriched is True
        mock_reg.enrich_merged.assert_called_once_with("sds", "64-17-5")

    @patch("global_sds.services.enrichment_service.default_registry", create=True)
    def test_should_handle_registry_failure(self, mock_registry_import):
        with patch(
            "global_sds.services.enrichment_service.default_registry",
            create=True,
        ) as mock_reg:
            mock_reg.enrich_merged.side_effect = Exception("timeout")

            service = SdsEnrichmentService()
            result = service.enrich({"product_name": "Acetone"})

        assert result.enriched is False
        assert "timeout" in result.errors[0]

    @patch("global_sds.services.enrichment_service.default_registry", create=True)
    def test_should_handle_empty_result(self, mock_registry_import):
        enriched = _make_enrichment_result(properties=None)

        with patch(
            "global_sds.services.enrichment_service.default_registry",
            create=True,
        ) as mock_reg:
            mock_reg.enrich_merged.return_value = enriched

            service = SdsEnrichmentService()
            result = service.enrich({"product_name": "Unknown"})

        assert result.enriched is False

    def test_should_handle_enrichment_not_installed(self):
        service = SdsEnrichmentService()
        with patch.dict("sys.modules", {"enrichment": None}):
            result = service.enrich({"product_name": "Acetone"})
        assert result.enriched is False
        assert "iil-enrichment not installed" in result.errors


class TestMergeIntoParseResult:
    """Tests for merge_into_parse_result."""

    def test_should_fill_empty_cas(self):
        service = SdsEnrichmentService()
        result = service.merge_into_parse_result(
            {"cas_number": "", "h_statements": []},
            SdsEnrichmentResult(
                enriched=True,
                cas_number="67-64-1",
                source="GESTIS",
            ),
        )
        assert result["cas_number"] == "67-64-1"

    def test_should_not_overwrite_existing_cas(self):
        service = SdsEnrichmentService()
        result = service.merge_into_parse_result(
            {"cas_number": "64-17-5"},
            SdsEnrichmentResult(
                enriched=True,
                cas_number="999-99-9",
                source="GESTIS",
            ),
        )
        assert result["cas_number"] == "64-17-5"

    def test_should_merge_h_statements(self):
        service = SdsEnrichmentService()
        result = service.merge_into_parse_result(
            {"h_statements": ["H225"]},
            SdsEnrichmentResult(
                enriched=True,
                h_statements=["H225", "H319", "H336"],
                source="GESTIS",
            ),
        )
        assert result["h_statements"] == ["H225", "H319", "H336"]

    def test_should_fill_signal_word_when_none(self):
        service = SdsEnrichmentService()
        result = service.merge_into_parse_result(
            {"signal_word": "none"},
            SdsEnrichmentResult(
                enriched=True,
                signal_word="Danger",
                source="GESTIS",
            ),
        )
        assert result["signal_word"] == "danger"

    def test_should_not_overwrite_existing_signal_word(self):
        service = SdsEnrichmentService()
        result = service.merge_into_parse_result(
            {"signal_word": "warning"},
            SdsEnrichmentResult(
                enriched=True,
                signal_word="Danger",
                source="GESTIS",
            ),
        )
        assert result["signal_word"] == "warning"

    def test_should_return_unchanged_when_not_enriched(self):
        service = SdsEnrichmentService()
        original = {"cas_number": "", "h_statements": []}
        result = service.merge_into_parse_result(
            original,
            SdsEnrichmentResult(enriched=False),
        )
        assert result == original
