"""
LLM adapter implementations for the supported cloud providers.

Supported providers are intentionally limited to Gemini and OpenAI. Local
fallback remains available for offline/dev runs.
"""

from __future__ import annotations

import importlib.util

from app.adapters.base import LLMAdapter
from app.config.model_registry import (
    DEFAULT_LLM_PROVIDER,
    LLM_FALLBACK_ORDER,
    LLM_PROVIDER_MODELS,
)
from app.utils.exceptions import ModelProviderError, classify_external_error
from app.utils.logging_utils import get_logger

log = get_logger(__name__)

# Rough USD estimates per 1K output tokens. Keep this aligned with the selected
# small model family; exact billing should be checked in provider consoles.
_COST_PER_1K = {
    "gemini": 0.0004,
    "openai": 0.004,
    "local": 0.0,
}


class GeminiAdapter(LLMAdapter):
    """Call the Gemini API through the current Google GenAI SDK."""

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self._api_key = api_key
        self._model = model or LLM_PROVIDER_MODELS["gemini"]
        self.provider = "gemini"
        self.estimated_cost_per_1k = _COST_PER_1K["gemini"]

    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        if not self._api_key:
            raise ModelProviderError(
                "Gemini API key is missing.",
                remediation="Set GEMINI_API_KEY in .env or use local fallback.",
            )
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ModelProviderError(
                f"google-genai package not installed: {exc}",
                remediation="Install dependencies with 'python -m pip install -r requirements.txt'.",
            ) from exc

        try:
            client = genai.Client(api_key=self._api_key)
            response = client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.3,
                ),
            )
            text = response.text or ""
        except Exception as exc:
            raise classify_external_error(exc, provider="Gemini") from exc
        if not text.strip():
            raise ModelProviderError(
                "Gemini returned an empty response.",
                remediation="Retry or use a fallback provider.",
            )
        return text


class OpenAIAdapter(LLMAdapter):
    """Call the OpenAI Responses API."""

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self._api_key = api_key
        self._model = model or LLM_PROVIDER_MODELS["openai"]
        self.provider = "openai"
        self.estimated_cost_per_1k = _COST_PER_1K["openai"]

    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        if not self._api_key:
            raise ModelProviderError(
                "OpenAI API key is missing.",
                remediation="Set OPENAI_API_KEY in .env or use local fallback.",
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ModelProviderError(
                f"openai package not installed: {exc}",
                remediation="Install dependencies with 'python -m pip install -r requirements.txt'.",
            ) from exc

        try:
            client = OpenAI(api_key=self._api_key)
            response = client.responses.create(
                model=self._model,
                input=prompt,
                max_output_tokens=max_tokens,
            )
            text = getattr(response, "output_text", "")
        except Exception as exc:
            raise classify_external_error(exc, provider="OpenAI") from exc
        if text:
            return text

        # Defensive fallback for SDK shapes that do not expose output_text.
        parts: list[str] = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                maybe_text = getattr(content, "text", "")
                if maybe_text:
                    parts.append(maybe_text)
        final_text = "\n".join(parts)
        if not final_text.strip():
            raise ModelProviderError(
                "OpenAI returned an empty or unsupported response shape.",
                remediation="Retry, upgrade the OpenAI SDK, or use a fallback provider.",
            )
        return final_text


class LocalFallbackAdapter(LLMAdapter):
    """Rule-based fallback used when cloud providers are unavailable."""

    provider = "local"
    estimated_cost_per_1k = 0.0

    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        prompt_lower = prompt.lower()
        if "summarize" in prompt_lower or "summary" in prompt_lower:
            return "[Local fallback] No usable cloud LLM configured - returning fallback summary."
        if "key point" in prompt_lower or "key points" in prompt_lower:
            return "1. [Local fallback] Key points unavailable without a usable cloud LLM."
        if "tag" in prompt_lower or "topic" in prompt_lower:
            return "general"
        if "answer" in prompt_lower or "question" in prompt_lower:
            return "[Local fallback] No usable cloud LLM configured - answer unavailable."
        return "[Local fallback] No usable cloud LLM configured."


def _provider_package_available(provider: str) -> bool:
    package_by_provider = {
        "gemini": "google.genai",
        "openai": "openai",
    }
    package = package_by_provider.get(provider)
    if not package:
        return False
    return importlib.util.find_spec(package) is not None


def build_llm_adapter(
    provider: str,
    model: str,
    api_keys: dict[str, str],
) -> LLMAdapter:
    """
    Build the best available LLM adapter.

    Priority: requested provider first, then configured fallback order.
    """
    effective_provider = provider or DEFAULT_LLM_PROVIDER
    effective_model = model or LLM_PROVIDER_MODELS.get(
        effective_provider, LLM_PROVIDER_MODELS[DEFAULT_LLM_PROVIDER]
    )
    candidates: list[tuple[str, str]] = [(effective_provider, effective_model)]
    for fallback_provider in LLM_FALLBACK_ORDER:
        candidates.append(
            (
                fallback_provider,
                LLM_PROVIDER_MODELS.get(fallback_provider, ""),
            )
        )

    tried: set[str] = set()
    for prov, mdl in candidates:
        if prov in tried:
            continue
        tried.add(prov)

        key = api_keys.get(prov, "")
        if not key:
            continue
        if not _provider_package_available(prov):
            log.warning(
                "Skipping %s adapter because required package is not installed.",
                prov,
            )
            continue

        try:
            if prov == "gemini":
                adapter = GeminiAdapter(api_key=key, model=mdl)
            elif prov == "openai":
                adapter = OpenAIAdapter(api_key=key, model=mdl)
            else:
                continue

            log.info("LLM adapter: %s / %s", adapter.provider, mdl)
            return adapter
        except Exception as exc:
            log.warning("Failed to initialise %s adapter: %s", prov, exc)

    log.warning("No usable LLM provider configured - using local fallback adapter.")
    return LocalFallbackAdapter()
