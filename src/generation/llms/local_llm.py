"""Local LLM scaffold."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core.interfaces import LLMProvider


class LocalLLM(LLMProvider):
    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> str:
        raise NotImplementedError("Local model support is scaffolded but not implemented.")
