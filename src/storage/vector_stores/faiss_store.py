"""FAISS vector store scaffold."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.core.interfaces import VectorStore
from src.core.models import Chunk, RetrievedChunk


class FaissVectorStore(VectorStore):
    def upsert(self, chunks: Sequence[Chunk], embeddings: Sequence[Sequence[float]]) -> None:
        raise NotImplementedError("FAISS support is scaffolded but not implemented.")

    def delete_document(self, document_id: str) -> None:
        raise NotImplementedError("FAISS support is scaffolded but not implemented.")

    def similarity_search(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int,
        filters: Mapping[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        raise NotImplementedError("FAISS support is scaffolded but not implemented.")
