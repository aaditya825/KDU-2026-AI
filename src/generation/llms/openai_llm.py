"""OpenAI chat provider implementation."""

from __future__ import annotations

from collections.abc import Mapping
import os
from typing import Any

from src.core.interfaces import LLMProvider


class OpenAILLM(LLMProvider):
    def __init__(
        self,
        *,
        model_name: str = "gpt-4o-mini",
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
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                metadata=dict(metadata or {}),
                timeout=self.request_timeout_seconds,
            )
        except Exception as exc:
            raise RuntimeError(
                "The OpenAI request failed. Check the API key, network access, and model configuration."
            ) from exc

        message = response.choices[0].message if response.choices else None
        content = getattr(message, "content", None) if message is not None else None
        if not content or not str(content).strip():
            raise RuntimeError("The OpenAI response did not contain any answer text.")
        return str(content).strip()

    def _get_client(self) -> object:
        if self._client is not None:
            return self._client
        if self.api_key is None and not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency guard.
            raise RuntimeError("The openai package is required for the default generator.") from exc
        self._client = OpenAI(api_key=self.api_key)
        return self._client
