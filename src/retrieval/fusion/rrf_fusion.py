"""Reciprocal Rank Fusion utilities."""

from __future__ import annotations

from copy import deepcopy

from src.core.models import RetrievedChunk


def reciprocal_rank_fusion(
    semantic_results: list[RetrievedChunk],
    keyword_results: list[RetrievedChunk],
    *,
    top_k: int,
    k: int = 60,
) -> list[RetrievedChunk]:
    """Fuse semantic and keyword results while deduplicating by chunk_id."""

    fused: dict[str, RetrievedChunk] = {}
    scores: dict[str, float] = {}
    best_rank: dict[str, int] = {}
    provenance: dict[str, set[str]] = {}

    for result_list, source_name in ((semantic_results, "semantic"), (keyword_results, "keyword")):
        for rank, item in enumerate(result_list, start=1):
            chunk_id = item.chunk.chunk_id
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
            best_rank[chunk_id] = min(best_rank.get(chunk_id, rank), rank)
            provenance.setdefault(chunk_id, set()).add(source_name)
            if chunk_id not in fused:
                fused[chunk_id] = deepcopy(item)
            fused[chunk_id].raw_scores[f"{source_name}_score"] = float(item.score or 0.0)
            fused[chunk_id].raw_scores[f"{source_name}_rank"] = float(rank)

    ordered = sorted(
        fused.values(),
        key=lambda item: (
            -scores.get(item.chunk.chunk_id, 0.0),
            best_rank.get(item.chunk.chunk_id, 10**9),
            item.chunk.chunk_id,
        ),
    )
    for rank, item in enumerate(ordered, start=1):
        item.rank = rank
        chunk_id = item.chunk.chunk_id
        item.retrieval_source = "+".join(sorted(provenance.get(chunk_id, {"hybrid"})))
        item.score = scores.get(chunk_id)
        item.raw_scores["rrf_score"] = float(item.score or 0.0)
    return ordered[:top_k]
