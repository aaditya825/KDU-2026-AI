"""Hybrid semantic + keyword retriever."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from src.core.interfaces import Retriever
from src.core.models import Query, RetrievedChunk
from src.retrieval.fusion.rrf_fusion import reciprocal_rank_fusion


@dataclass(slots=True)
class HybridRetriever(Retriever):
    semantic_retriever: Retriever
    keyword_retriever: Retriever
    fused_top_k: int = 10
    fusion_strategy: Callable[..., list[RetrievedChunk]] = field(default=reciprocal_rank_fusion)

    def retrieve(self, query: Query) -> list[RetrievedChunk]:
        semantic_results = self.semantic_retriever.retrieve(query)
        keyword_results = self.keyword_retriever.retrieve(query)
        requested_top_k = self._resolve_top_k(query)
        return self.fusion_strategy(semantic_results, keyword_results, top_k=requested_top_k)

    def _resolve_top_k(self, query: Query) -> int:
        override = query.metadata.get("fused_top_k")
        if isinstance(override, int) and override > 0:
            return override
        return self.fused_top_k
