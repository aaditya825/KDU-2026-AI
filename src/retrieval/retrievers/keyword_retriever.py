"""Keyword retriever implementation."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.interfaces import KeywordStore, Retriever
from src.core.models import Query, RetrievedChunk


@dataclass(slots=True)
class KeywordRetriever(Retriever):
    keyword_store: KeywordStore
    top_k: int = 10

    def retrieve(self, query: Query) -> list[RetrievedChunk]:
        requested_top_k = self._resolve_top_k(query)
        results = self.keyword_store.keyword_search(
            query.query_text,
            top_k=requested_top_k,
            filters=query.filters,
        )
        for rank, item in enumerate(results, start=1):
            item.retrieval_source = "keyword"
            item.rank = rank
            if item.score is not None:
                item.raw_scores.setdefault("keyword_score", float(item.score))
            item.raw_scores["keyword_rank"] = float(rank)
        return results

    def _resolve_top_k(self, query: Query) -> int:
        override = query.metadata.get("keyword_top_k")
        if isinstance(override, int) and override > 0:
            return override
        return self.top_k
