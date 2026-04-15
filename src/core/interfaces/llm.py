"""Interface for answer-generation models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


class LLMProvider(ABC):
    """Generates grounded answers from prepared prompts."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> str:
        """Generate a response for the provided prompt."""
