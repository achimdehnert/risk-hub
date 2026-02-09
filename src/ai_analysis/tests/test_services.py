"""Tests for AI hazard analysis services."""

import json

from ai_analysis.services import _parse_json_response


class TestParseJsonResponse:
    """Test JSON extraction from LLM responses."""

    def test_should_parse_plain_json(self):
        raw = '{"risk_level": "high", "summary": "Gefahr"}'
        result = _parse_json_response(raw)
        assert result["risk_level"] == "high"

    def test_should_parse_json_in_markdown_fence(self):
        raw = '```json\n{"risk_level": "low"}\n```'
        result = _parse_json_response(raw)
        assert result["risk_level"] == "low"

    def test_should_parse_json_in_plain_fence(self):
        raw = '```\n{"key": "val"}\n```'
        result = _parse_json_response(raw)
        assert result["key"] == "val"

    def test_should_return_raw_on_invalid_json(self):
        raw = "This is not JSON at all"
        result = _parse_json_response(raw)
        assert result["_parse_error"] is True
        assert result["_raw_text"] == raw

    def test_should_handle_nested_json(self):
        data = {
            "hazards": [
                {
                    "type": "explosion",
                    "severity": "high",
                }
            ],
            "zone_recommendations": [],
        }
        raw = json.dumps(data)
        result = _parse_json_response(raw)
        assert len(result["hazards"]) == 1
        assert result["hazards"][0]["type"] == "explosion"

    def test_should_strip_whitespace(self):
        raw = '  \n  {"ok": true}  \n  '
        result = _parse_json_response(raw)
        assert result["ok"] is True
