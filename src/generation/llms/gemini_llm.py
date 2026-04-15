"""Gemini chat provider implementation."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from src.core.interfaces import LLMProvider


class GeminiLLM(LLMProvider):
    def __init__(
        self,
        *,
        model_name: str = "gemini-2.5-flash",
        temperature: float = 0.1,
        max_tokens: int = 800,
        request_timeout_seconds: float = 60.0,
        api_key: str | None = None,
        client: object | None = None,
    ) -> None:
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.request_timeout_seconds = request_timeout_seconds
        self.api_key = api_key
        self._client = client

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> str:
        client = self._get_client()
        config = self._build_config(system_prompt)
        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
        except Exception as exc:
            raise RuntimeError(
                "The Gemini request failed. Check the API key, network access, and model configuration."
            ) from exc

        text = getattr(response, "text", None)
        if not text or not str(text).strip():
            raise RuntimeError("The Gemini response did not contain any answer text.")
        return str(text).strip()

    def _build_config(self, system_prompt: str | None) -> object:
        try:
            from google.genai import types
        except ImportError:
            return {
                "system_instruction": system_prompt,
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            }
        return types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
        )

    def _get_client(self) -> object:
        if self._client is not None:
            return self._client
        if self.api_key is None and not os.environ.get("GEMINI_API_KEY"):
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover - dependency guard.
            raise RuntimeError("The google-genai package is required for the default Gemini generator.") from exc
        self._client = genai.Client(api_key=self.api_key)
        return self._client
