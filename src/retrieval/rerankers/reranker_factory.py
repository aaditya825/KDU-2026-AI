"""Factory for rerankers."""

from __future__ import annotations

from src.core.interfaces import Reranker
from src.retrieval.rerankers.cross_encoder_reranker import CrossEncoderReranker
from src.retrieval.rerankers.llm_reranker import LLMReranker


class RerankerFactory:
    _registry: dict[str, type[Reranker]] = {
        "cross-encoder": CrossEncoderReranker,
        "llm": LLMReranker,
    }

    @classmethod
    def register(cls, name: str, reranker_cls: type[Reranker]) -> None:
        cls._registry[name.lower()] = reranker_cls

    @classmethod
    def create(cls, name: str, **kwargs: object) -> Reranker:
        try:
            reranker_cls = cls._registry[name.lower()]
        except KeyError as exc:
            raise ValueError(f"Unsupported reranker '{name}'.") from exc
        return reranker_cls(**kwargs)

    @classmethod
    def create_default(cls, **kwargs: object) -> Reranker:
        return cls.create("cross-encoder", **kwargs)
