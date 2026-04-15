"""Factory for vector stores."""

from __future__ import annotations

from src.core.interfaces import VectorStore
from src.storage.vector_stores.chroma_store import ChromaVectorStore
from src.storage.vector_stores.faiss_store import FaissVectorStore


class VectorStoreFactory:
    _registry: dict[str, type[VectorStore]] = {
        "chromadb": ChromaVectorStore,
        "chroma": ChromaVectorStore,
        "faiss": FaissVectorStore,
    }

    @classmethod
    def register(cls, name: str, store_cls: type[VectorStore]) -> None:
        cls._registry[name.lower()] = store_cls

    @classmethod
    def create(cls, name: str, **kwargs: object) -> VectorStore:
        try:
            store_cls = cls._registry[name.lower()]
        except KeyError as exc:
            raise ValueError(f"Unsupported vector store '{name}'.") from exc
        return store_cls(**kwargs)
