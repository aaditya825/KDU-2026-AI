import pytest

from src.llm_client.client import LLMClient


def test_mock_llm_client_generates_text_and_usage() -> None:
    client = LLMClient(provider_mode="mock")

    result = client.generate(
        prompt="Prompt content",
        model_id="mock-economy",
        query="What are your hours?",
        category="FAQ",
        mode="normal",
    )

    assert result.provider == "mock"
    assert result.model_id == "mock-economy"
    assert "What are your hours?" in result.text
    assert result.usage_details["total_tokens"] > 0


def test_mock_llm_client_classifies_query_and_returns_usage() -> None:
    client = LLMClient(provider_mode="mock")

    result = client.classify_query(
        query="Can I cancel my booking and get a refund?",
        model_id="gemini-2.5-flash-lite",
        confidence_threshold=0.65,
    )

    assert result.model_id == "gemini-2.5-flash-lite"
    assert result.source == "gemini-classifier-mock"
    assert result.usage_details["total_tokens"] > 0


def test_gemini_client_requires_api_key() -> None:
    with pytest.raises(ValueError):
        LLMClient(provider_mode="gemini", api_key="")
