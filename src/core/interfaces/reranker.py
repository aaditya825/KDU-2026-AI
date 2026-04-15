"""Interface for rerankers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from src.core.models import Query, RetrievedChunk


class Reranker(ABC):
    """Scores and reorders retrieved chunks."""

    @abstractmethod
    def rerank(self, query: Query, candidates: Sequence[RetrievedChunk], *, top_k: int) -> list[RetrievedChunk]:
        """Rerank candidate chunks for the supplied query."""

    def is_available(self) -> bool:
        """Report whether the reranker can run in the current environment."""
        return True
