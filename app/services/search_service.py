"""
app/services/search_service.py
────────────────────────────────
Semantic search over a processed file's vector index.

Flow:
  1. Embed the user query with the EmbeddingAdapter.
  2. Query the VectorStore for the top-k nearest chunks.
  3. Return SearchResult objects with scores, confidence, and metadata.

Low-confidence chunks are included in results but flagged clearly so callers
can surface the uncertainty to users.
"""

from __future__ import annotations

import time

from app.adapters.base import EmbeddingAdapter
from app.adapters.vector_store_adapter import VectorStore
from app.models.domain import SearchResult
from app.utils.logging_utils import get_logger

log = get_logger(__name__)

_LOW_CONF_THRESHOLD = 0.4


class SearchService:
    """Run semantic search for a single file."""

    def __init__(self, embedding_adapter: EmbeddingAdapter, vector_store: VectorStore) -> None:
        self._embed = embedding_adapter
        self._store = vector_store

    def search(self, file_id: str, query: str, top_k: int = 5) -> list[SearchResult]:
        """
        Embed *query* and return the top-k most relevant chunks for *file_id*.

        Low-confidence chunks are not discarded — they are returned with their
        original confidence score so the caller can decide how to surface them.
        """
        if not query.strip():
            return []

        t0 = time.monotonic()
        query_embedding = self._embed.embed_query(query)
        results = self._store.search(file_id, query_embedding, top_k=top_k)

        for r in results:
            if r.confidence < _LOW_CONF_THRESHOLD:
                log.warning(
                    "Low-confidence chunk included in results",
                    extra={"file_id": file_id, "chunk_index": r.chunk_index, "confidence": r.confidence},
                )

        latency = int((time.monotonic() - t0) * 1000)
        log.info(
            "Search complete",
            extra={"file_id": file_id, "query_len": len(query), "hits": len(results), "latency_ms": latency},
        )
        return results
