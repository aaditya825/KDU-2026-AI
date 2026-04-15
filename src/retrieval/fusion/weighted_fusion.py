"""Alternative weighted fusion helper."""

from __future__ import annotations

from src.core.models import RetrievedChunk


def weighted_score_fusion(
    semantic_results: list[RetrievedChunk],
    keyword_results: list[RetrievedChunk],
    *,
    top_k: int,
    semantic_weight: float = 0.5,
    keyword_weight: float = 0.5,
) -> list[RetrievedChunk]:
    fused: dict[str, RetrievedChunk] = {}
    scores: dict[str, float] = {}
    for results, source_name, weight in (
        (semantic_results, "semantic", semantic_weight),
        (keyword_results, "keyword", keyword_weight),
    ):
        for item in results:
            chunk_id = item.chunk.chunk_id
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weight * (item.score or 0.0)
            if chunk_id not in fused:
                fused[chunk_id] = item
            fused[chunk_id].raw_scores[source_name] = item.score or 0.0

    ordered = sorted(fused.values(), key=lambda item: scores.get(item.chunk.chunk_id, 0.0), reverse=True)
    for rank, item in enumerate(ordered, start=1):
        item.rank = rank
        item.retrieval_source = "hybrid"
        item.score = scores.get(item.chunk.chunk_id)
    return ordered[:top_k]
