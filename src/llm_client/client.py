"""LLM client abstraction with mock and Gemini provider implementations."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib import error, parse, request

from src.classifier.rules import classify_with_rules
from src.core.models import ClassificationResult, GenerationResult


class MockProviderAdapter:
    """Local-safe adapter used for development and tests."""

    def generate(self, prompt: str, model_id: str, **kwargs: Any) -> GenerationResult:
        query = kwargs.get("query", "")
        mode = kwargs.get("mode", "normal")
        category = kwargs.get("category", "general")

        usage_details = self._build_usage(prompt, query)
        prefix = "Degraded mode:" if mode == "degraded" else "Response:"
        response_text = (
            f"{prefix} handled as {category} using {model_id}. "
            f"Customer query: {query}"
        )

        return GenerationResult(
            model_id=model_id,
            provider="mock",
            text=response_text,
            usage_details=usage_details,
        )

    def classify_query(
        self,
        query: str,
        model_id: str,
        confidence_threshold: float,
    ) -> ClassificationResult:
        prompt = _build_classification_prompt(query, confidence_threshold)
        usage_details = self._build_usage(prompt, query)
        rule_result = classify_with_rules(query).result
        return rule_result.model_copy(
            update={
                "source": "gemini-classifier-mock",
                "model_id": model_id,
                "usage_details": usage_details,
            }
        )

    @staticmethod
    def _build_usage(prompt: str, query: str) -> dict[str, int]:
        prompt_tokens = max(1, len(prompt.split()))
        completion_tokens = max(12, len(query.split()) + 8)
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }


class GeminiProviderAdapter:
    """Gemini REST adapter using the Generative Language API."""

    def __init__(self, *, api_key: str, base_url: str, timeout_seconds: int) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required when PROVIDER_MODE=gemini.")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def generate(self, prompt: str, model_id: str, **kwargs: Any) -> GenerationResult:
        raw_response = self._request_content(prompt=prompt, model_id=model_id)

        response_text = self._extract_text(raw_response)
        usage_details = self._extract_usage(raw_response)
        return GenerationResult(
            model_id=model_id,
            provider="gemini",
            text=response_text,
            usage_details=usage_details,
        )

    def classify_query(
        self,
        query: str,
        model_id: str,
        confidence_threshold: float,
    ) -> ClassificationResult:
        prompt = _build_classification_prompt(query, confidence_threshold)
        raw_response = self._request_content(prompt=prompt, model_id=model_id)
        response_text = self._extract_text(raw_response)
        payload = self._extract_json_object(response_text)

        try:
            classification = ClassificationResult.model_validate(payload)
        except Exception as exc:
            raise RuntimeError(
                f"Gemini classification payload was invalid: {response_text}"
            ) from exc

        return classification.model_copy(
            update={
                "source": "gemini-classifier",
                "model_id": model_id,
                "usage_details": self._extract_usage(raw_response),
            }
        )

    def _request_content(self, *, prompt: str, model_id: str) -> dict[str, Any]:
        endpoint = (
            f"{self.base_url}/models/{model_id}:generateContent?"
            f"{parse.urlencode({'key': self.api_key})}"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt,
                        }
                    ]
                }
            ]
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini API error ({exc.code}): {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Gemini API request failed: {exc.reason}") from exc

    @staticmethod
    def _extract_text(raw_response: dict[str, Any]) -> str:
        candidates = raw_response.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini API response did not contain any candidates.")

        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [part.get("text", "") for part in parts if "text" in part]
        combined = "\n".join(text for text in texts if text).strip()
        if not combined:
            raise RuntimeError("Gemini API response did not contain text content.")
        return combined

    @staticmethod
    def _extract_json_object(response_text: str) -> dict[str, Any]:
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match is None:
                raise RuntimeError(f"Gemini classification response was not valid JSON: {response_text}")
            try:
                payload = json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Gemini classification response was not valid JSON: {response_text}"
                ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError(f"Gemini classification response was not an object: {response_text}")
        return payload

    @staticmethod
    def _extract_usage(raw_response: dict[str, Any]) -> dict[str, int]:
        usage = raw_response.get("usageMetadata", {})
        prompt_tokens = int(usage.get("promptTokenCount", 0))
        completion_tokens = int(usage.get("candidatesTokenCount", 0))
        total_tokens = int(usage.get("totalTokenCount", prompt_tokens + completion_tokens))
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }


class LLMClient:
    """Abstraction boundary for provider-specific model calls."""

    def __init__(
        self,
        provider_mode: str = "mock",
        *,
        api_key: str | None = None,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_seconds: int = 30,
    ) -> None:
        self.provider_mode = provider_mode

        if provider_mode == "mock":
            self._adapter = MockProviderAdapter()
        elif provider_mode == "gemini":
            self._adapter = GeminiProviderAdapter(
                api_key=api_key or "",
                base_url=base_url,
                timeout_seconds=timeout_seconds,
            )
        else:
            raise ValueError(f"Unsupported provider mode: {provider_mode}")

    def generate(self, prompt: str, model_id: str, **kwargs: Any) -> GenerationResult:
        """Generate a response from the configured provider adapter."""
        return self._adapter.generate(prompt=prompt, model_id=model_id, **kwargs)

    def classify_query(
        self,
        *,
        query: str,
        model_id: str,
        confidence_threshold: float,
    ) -> ClassificationResult:
        """Classify a query using the configured provider adapter."""
        return self._adapter.classify_query(
            query=query,
            model_id=model_id,
            confidence_threshold=confidence_threshold,
        )


def _build_classification_prompt(query: str, confidence_threshold: float) -> str:
    """Return a strict JSON-only prompt for query classification."""
    return (
        "Classify the customer-support query and return JSON only.\n"
        'Allowed categories: ["FAQ", "booking", "complaint"]\n'
        'Allowed complexity values: ["low", "medium", "high"]\n'
        'Allowed expected_response_type values: ["simple", "standard", "complex"]\n'
        f"Use confidence below {confidence_threshold:.2f} only when the intent is ambiguous, conflicting, or unclear.\n"
        "If multiple intents appear, choose the dominant one based on what the customer most urgently needs help with.\n"
        "Return exactly this JSON object shape with no markdown:\n"
        '{'
        '"category":"FAQ",'
        '"complexity":"low",'
        '"expected_response_type":"simple",'
        '"confidence":0.0'
        '}\n'
        f"Query: {query}"
    )
