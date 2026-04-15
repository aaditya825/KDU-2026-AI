"""Factory for chunking strategies."""

from __future__ import annotations

from src.core.interfaces import Chunker
from src.ingestion.chunkers.contextual_chunker import ContextualChunker
from src.ingestion.chunkers.recursive_chunker import RecursiveChunker
from src.ingestion.chunkers.semantic_chunker import SemanticChunker


class ChunkerFactory:
    _registry: dict[str, type[Chunker]] = {
        "contextual": ContextualChunker,
        "recursive": RecursiveChunker,
        "semantic": SemanticChunker,
    }

    @classmethod
    def register(cls, name: str, chunker_cls: type[Chunker]) -> None:
        cls._registry[name.lower()] = chunker_cls

    @classmethod
    def create(cls, name: str, **kwargs: object) -> Chunker:
        try:
            chunker_cls = cls._registry[name.lower()]
        except KeyError as exc:
            raise ValueError(f"Unsupported chunker '{name}'.") from exc
        return chunker_cls(**kwargs)

    @classmethod
    def create_default(cls, *, chunk_size: int = 512, overlap: int = 50) -> Chunker:
        return cls.create("contextual", chunk_size=chunk_size, overlap=overlap)
