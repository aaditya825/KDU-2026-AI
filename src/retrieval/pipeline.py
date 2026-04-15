"""Retrieval pipeline with graceful reranker fallback."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.interfaces import Reranker, Retriever
from src.core.models import Query, RetrievedChunk
from src.utils.logger import get_logger


logger = get_logger(__name__)


@dataclass(slots=True)
class RetrievalPipeline:
    retriever: Retriever
    reranker: Reranker | None = None
    rerank_top_k: int = 10
    final_top_k: int = 5

    def retrieve(self, query: Query) -> list[RetrievedChunk]:
        logger.info("event=retrieval.start session_id=%s", query.session_id)
        candidates = self.retriever.retrieve(query)
        if not candidates:
            logger.info("event=retrieval.empty session_id=%s", query.session_id)
            return []

        rerank_limit = self._resolve_rerank_top_k(query)
        final_limit = self._resolve_final_top_k(query)
        fused_candidates = candidates[:rerank_limit]

        if self.reranker and self.reranker.is_available():
            try:
                reranked = self.reranker.rerank(query, fused_candidates, top_k=final_limit)
                logger.info(
                    "event=reranking.complete session_id=%s candidate_count=%s returned_count=%s",
                    query.session_id,
                    len(fused_candidates),
                    len(reranked),
                )
                return reranked
            except Exception:
                logger.exception("event=reranking.failed session_id=%s", query.session_id)
                pass

        fallback = fused_candidates[:final_limit]
        for rank, item in enumerate(fallback, start=1):
            item.rank = rank
            item.raw_scores.setdefault("fallback_to_fused", 1.0)
        logger.info(
            "event=retrieval.fallback_to_fused session_id=%s candidate_count=%s returned_count=%s",
            query.session_id,
            len(fused_candidates),
            len(fallback),
        )
        return fallback

    def _resolve_rerank_top_k(self, query: Query) -> int:
        override = query.metadata.get("rerank_top_k")
        if isinstance(override, int) and override > 0:
            return override
        return self.rerank_top_k

    def _resolve_final_top_k(self, query: Query) -> int:
        configured = self.final_top_k
        if query.top_k > 0:
            configured = min(configured, query.top_k)
        override = query.metadata.get("final_top_k")
        if isinstance(override, int) and override > 0:
            configured = min(configured, override)
        return configured
