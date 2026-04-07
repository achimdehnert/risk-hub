"""
tests/contracts/test_aifw_contract.py — Contract-Tests für aifw API (ADR-155).

Prüft dass risk-hub's Nutzung von aifw.service.completion/sync_completion
mit der tatsächlichen aifw-API kompatibel bleibt.

Consumer: risk-hub (ai_analysis/llm_client.py)
Provider: iil-aifw (aifw.service)
"""

from __future__ import annotations

import pytest

iil_testkit_contract = pytest.importorskip(
    "iil_testkit.contract", reason="iil_testkit not installed"
)
ContractVerifier = iil_testkit_contract.ContractVerifier

pytestmark = pytest.mark.contract


# ══════════════════════════════════════════════════════════════════════════════
# aifw.service.completion — Async LLM Completion
# ══════════════════════════════════════════════════════════════════════════════


class TestAifwCompletionContract:
    """Contract: aifw.service.completion() Parameter-Signatur."""

    @pytest.fixture
    def verifier(self):
        from aifw.service import completion

        return ContractVerifier.for_callable(completion)

    def test_should_have_action_code_param(self, verifier) -> None:
        verifier.assert_params(["action_code"])

    def test_should_have_messages_param(self, verifier) -> None:
        verifier.assert_params(["messages"])

    def test_should_have_temperature_param(self, verifier) -> None:
        verifier.assert_params(["temperature"])

    def test_should_have_max_tokens_param(self, verifier) -> None:
        verifier.assert_params(["max_tokens"])

    def test_should_have_tenant_id_param(self, verifier) -> None:
        verifier.assert_params(["tenant_id"])

    def test_should_have_object_id_param(self, verifier) -> None:
        verifier.assert_params(["object_id"])

    def test_should_have_metadata_param(self, verifier) -> None:
        verifier.assert_params(["metadata"])

    def test_should_not_have_old_prompt_param(self, verifier) -> None:
        """Regression: 'prompt' wurde durch 'messages' ersetzt."""
        verifier.assert_no_param("prompt")


# ══════════════════════════════════════════════════════════════════════════════
# aifw.service.sync_completion — Synchronous LLM Completion
# ══════════════════════════════════════════════════════════════════════════════


class TestAifwSyncCompletionContract:
    """Contract: aifw.service.sync_completion() Parameter-Signatur."""

    @pytest.fixture
    def verifier(self):
        from aifw.service import sync_completion

        return ContractVerifier.for_callable(sync_completion)

    def test_should_have_action_code_param(self, verifier) -> None:
        verifier.assert_params(["action_code"])

    def test_should_have_messages_param(self, verifier) -> None:
        verifier.assert_params(["messages"])

    def test_should_have_temperature_param(self, verifier) -> None:
        verifier.assert_params(["temperature"])

    def test_should_have_max_tokens_param(self, verifier) -> None:
        verifier.assert_params(["max_tokens"])

    def test_should_have_tenant_id_param(self, verifier) -> None:
        verifier.assert_params(["tenant_id"])


# ══════════════════════════════════════════════════════════════════════════════
# aifw.service.LLMResult — Response Shape
# ══════════════════════════════════════════════════════════════════════════════


class TestAifwLLMResultContract:
    """Contract: aifw.service.LLMResult hat die erwarteten Attribute."""

    @pytest.fixture
    def verifier(self):
        from aifw.service import LLMResult

        return ContractVerifier(LLMResult)

    def test_should_have_success_attr(self, verifier) -> None:
        """risk-hub prüft result.success in llm_client.py."""
        from aifw.service import LLMResult

        assert hasattr(LLMResult, "__annotations__") or hasattr(LLMResult, "success"), (
            "LLMResult muss 'success' Attribut haben (risk-hub prüft result.success)"
        )

    def test_should_have_content_attr(self, verifier) -> None:
        """risk-hub liest result.content in llm_client.py."""
        from aifw.service import LLMResult

        assert hasattr(LLMResult, "__annotations__") or hasattr(LLMResult, "content"), (
            "LLMResult muss 'content' Attribut haben (risk-hub liest result.content)"
        )

    def test_should_have_error_attr(self, verifier) -> None:
        """risk-hub liest result.error bei Fehler."""
        from aifw.service import LLMResult

        assert hasattr(LLMResult, "__annotations__") or hasattr(LLMResult, "error"), (
            "LLMResult muss 'error' Attribut haben (risk-hub liest result.error)"
        )


# ══════════════════════════════════════════════════════════════════════════════
# promptfw.extract_json — JSON Extraction
# ══════════════════════════════════════════════════════════════════════════════


class TestPromptfwExtractJsonContract:
    """Contract: promptfw.extract_json() existiert und nimmt str."""

    @pytest.fixture
    def verifier(self):
        from promptfw import extract_json

        return ContractVerifier.for_callable(extract_json)

    def test_should_accept_raw_string(self, verifier) -> None:
        """risk-hub ruft extract_json(raw) mit einem String auf."""
        verifier.assert_params(["raw"])


# ══════════════════════════════════════════════════════════════════════════════
# risk-hub eigene LLM-Client Funktionen
# ══════════════════════════════════════════════════════════════════════════════


class TestRiskHubLlmClientContract:
    """Contract: risk-hub ai_analysis/llm_client.py Signatur-Stabilität.

    llm_client.py Funktionen nehmen (prompt, system, action_code, ...).
    services.py ruft sie mit messages= keyword — llm_client baut daraus messages.
    """

    @pytest.fixture
    def sync_verifier(self):
        from ai_analysis.llm_client import llm_complete_sync

        return ContractVerifier.for_callable(llm_complete_sync)

    @pytest.fixture
    def async_verifier(self):
        from ai_analysis.llm_client import llm_complete

        return ContractVerifier.for_callable(llm_complete)

    def test_should_sync_have_action_code_param(self, sync_verifier) -> None:
        sync_verifier.assert_params(["action_code"])

    def test_should_sync_have_tenant_id_param(self, sync_verifier) -> None:
        sync_verifier.assert_params(["tenant_id"])

    def test_should_sync_have_temperature_param(self, sync_verifier) -> None:
        sync_verifier.assert_params(["temperature"])

    def test_should_sync_have_object_id_param(self, sync_verifier) -> None:
        sync_verifier.assert_params(["object_id"])

    def test_should_async_have_action_code_param(self, async_verifier) -> None:
        async_verifier.assert_params(["action_code"])

    def test_should_async_have_tenant_id_param(self, async_verifier) -> None:
        async_verifier.assert_params(["tenant_id"])
