"""Factory for LLM providers."""

from __future__ import annotations

from src.core.interfaces import LLMProvider
from src.generation.llms.anthropic_llm import AnthropicLLM
from src.generation.llms.gemini_llm import GeminiLLM
from src.generation.llms.local_llm import LocalLLM
from src.generation.llms.openai_llm import OpenAILLM


class LLMFactory:
    _registry: dict[str, type[LLMProvider]] = {
        "gemini": GeminiLLM,
        "openai": OpenAILLM,
        "anthropic": AnthropicLLM,
        "local": LocalLLM,
    }

    @classmethod
    def register(cls, name: str, provider_cls: type[LLMProvider]) -> None:
        cls._registry[name.lower()] = provider_cls

    @classmethod
    def create(cls, name: str, **kwargs: object) -> LLMProvider:
        try:
            provider_cls = cls._registry[name.lower()]
        except KeyError as exc:
            raise ValueError(f"Unsupported LLM provider '{name}'.") from exc
        return provider_cls(**kwargs)

    @classmethod
    def create_default(cls, **kwargs: object) -> LLMProvider:
        return cls.create("gemini", **kwargs)
