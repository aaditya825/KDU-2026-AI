"""Interface for chunking strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from src.core.models import Chunk, Document


class Chunker(ABC):
    """Splits a document into traceable chunks."""

    @abstractmethod
    def chunk(self, document: Document) -> Sequence[Chunk]:
        """Create chunks for the provided document."""
