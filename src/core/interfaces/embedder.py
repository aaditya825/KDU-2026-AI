"""Interface for embedding providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence


class Embedder(ABC):
    """Generates vector embeddings for chunks and queries."""

    @abstractmethod
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed multiple text inputs."""

    @abstractmethod
    def embed_query(self, query_text: str) -> list[float]:
        """Embed a single query string."""
