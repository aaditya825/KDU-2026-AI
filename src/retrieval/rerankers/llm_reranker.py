"""LLM reranker scaffold."""

from __future__ import annotations

from collections.abc import Sequence

from src.core.interfaces import Reranker
from src.core.models import Query, RetrievedChunk


class LLMReranker(Reranker):
    def rerank(self, query: Query, candidates: Sequence[RetrievedChunk], *, top_k: int) -> list[RetrievedChunk]:
        raise NotImplementedError("LLM reranking is scaffolded but not implemented.")

    def is_available(self) -> bool:
        return False
