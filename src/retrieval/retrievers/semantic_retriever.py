"""Semantic retriever implementation."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.interfaces import Embedder, Retriever, VectorStore
from src.core.models import Query, RetrievedChunk


@dataclass(slots=True)
class SemanticRetriever(Retriever):
    embedder: Embedder
    vector_store: VectorStore
    top_k: int = 10

    def retrieve(self, query: Query) -> list[RetrievedChunk]:
        requested_top_k = self._resolve_top_k(query)
        query_embedding = self.embedder.embed_query(query.query_text)
        results = self.vector_store.similarity_search(
            query_embedding,
            top_k=requested_top_k,
            filters=query.filters,
        )
        for rank, item in enumerate(results, start=1):
            item.retrieval_source = "semantic"
            item.rank = rank
            if item.score is not None:
                item.raw_scores.setdefault("semantic_score", float(item.score))
            item.raw_scores["semantic_rank"] = float(rank)
        return results

    def _resolve_top_k(self, query: Query) -> int:
        override = query.metadata.get("semantic_top_k")
        if isinstance(override, int) and override > 0:
            return override
        return self.top_k
