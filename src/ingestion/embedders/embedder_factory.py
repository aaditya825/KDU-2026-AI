"""Factory for embedding providers."""

from __future__ import annotations

from src.core.interfaces import Embedder
from src.ingestion.embedders.openai_embedder import OpenAIEmbedder
from src.ingestion.embedders.sentence_transformer_embedder import SentenceTransformerEmbedder


class EmbedderFactory:
    _registry: dict[str, type[Embedder]] = {
        "sentence-transformers": SentenceTransformerEmbedder,
        "openai": OpenAIEmbedder,
    }

    @classmethod
    def register(cls, name: str, embedder_cls: type[Embedder]) -> None:
        cls._registry[name.lower()] = embedder_cls

    @classmethod
    def create(cls, name: str, **kwargs: object) -> Embedder:
        try:
            embedder_cls = cls._registry[name.lower()]
        except KeyError as exc:
            raise ValueError(f"Unsupported embedder '{name}'.") from exc
        return embedder_cls(**kwargs)

    @classmethod
    def create_default(cls, **kwargs: object) -> Embedder:
        return cls.create("sentence-transformers", **kwargs)
