"""Semantic chunker scaffold."""

from __future__ import annotations

from src.core.interfaces import Chunker
from src.core.models import Chunk, Document


class SemanticChunker(Chunker):
    def chunk(self, document: Document) -> list[Chunk]:
        raise NotImplementedError("Semantic chunking will be implemented in a later task.")
