"""Cross-encoder reranker implementation."""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy

from src.core.interfaces import Reranker
from src.core.models import Query, RetrievedChunk


class CrossEncoderReranker(Reranker):
    def __init__(
        self,
        *,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        model: object | None = None,
    ) -> None:
        self.model_name = model_name
        self._model = model
        self._load_error: Exception | None = None

    def rerank(self, query: Query, candidates: Sequence[RetrievedChunk], *, top_k: int) -> list[RetrievedChunk]:
        if not candidates or top_k <= 0:
            return []
        model = self._get_model()
        pairs = [[query.query_text, candidate.chunk.text] for candidate in candidates]
        scores = model.predict(pairs)

        reranked: list[RetrievedChunk] = []
        for candidate, score in zip(candidates, scores, strict=False):
            updated = deepcopy(candidate)
            updated.retrieval_source = f"{candidate.retrieval_source}|reranked"
            updated.raw_scores["pre_rerank_score"] = float(candidate.score or 0.0)
            updated.raw_scores["reranker_score"] = float(score)
            updated.score = float(score)
            reranked.append(updated)

        reranked.sort(key=lambda item: (-float(item.score or 0.0), item.chunk.chunk_id))
        for rank, item in enumerate(reranked, start=1):
            item.rank = rank
        return reranked[:top_k]

    def is_available(self) -> bool:
        try:
            self._get_model()
        except Exception:
            return False
        return True

    def _get_model(self) -> object:
        if self._model is not None:
            return self._model
        if self._load_error is not None:
            raise self._load_error
        try:
            from sentence_transformers import CrossEncoder
        except Exception as exc:  # pragma: no cover - dependency guard.
            self._load_error = exc
            raise
        try:
            self._model = CrossEncoder(self.model_name)
            return self._model
        except Exception as exc:
            self._load_error = exc
            raise
