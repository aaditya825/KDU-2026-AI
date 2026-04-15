"""Interface for retrieval strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.models import Query, RetrievedChunk


class Retriever(ABC):
    """Returns candidate chunks for a user query."""

    @abstractmethod
    def retrieve(self, query: Query) -> list[RetrievedChunk]:
        """Retrieve candidate chunks for the supplied query."""
