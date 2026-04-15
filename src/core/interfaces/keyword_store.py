"""Interface for keyword indexing and retrieval."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any

from src.core.models import Chunk, RetrievedChunk


class KeywordStore(ABC):
    """Persists chunks in a keyword-searchable index."""

    @abstractmethod
    def upsert(self, chunks: Sequence[Chunk]) -> None:
        """Create or update keyword entries for chunks."""

    @abstractmethod
    def delete_document(self, document_id: str) -> None:
        """Remove all keyword entries associated with a document."""

    @abstractmethod
    def keyword_search(
        self,
        query_text: str,
        *,
        top_k: int,
        filters: Mapping[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """Return keyword matches for the supplied query."""
