"""Interface for vector storage and similarity search."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any

from src.core.models import Chunk, RetrievedChunk


class VectorStore(ABC):
    """Persists chunk embeddings and performs semantic search."""

    @abstractmethod
    def upsert(self, chunks: Sequence[Chunk], embeddings: Sequence[Sequence[float]]) -> None:
        """Create or update vectors for the supplied chunks."""

    @abstractmethod
    def delete_document(self, document_id: str) -> None:
        """Remove all vectors associated with a document."""

    @abstractmethod
    def similarity_search(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int,
        filters: Mapping[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """Return the best semantic matches for a query embedding."""
