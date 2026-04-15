from __future__ import annotations

import unittest

from src.core.models import Chunk, Query, RetrievedChunk
from src.retrieval.fusion.rrf_fusion import reciprocal_rank_fusion
from src.retrieval.pipeline import RetrievalPipeline
from src.retrieval.rerankers.cross_encoder_reranker import CrossEncoderReranker
from src.retrieval.retrievers.keyword_retriever import KeywordRetriever
from src.retrieval.retrievers.semantic_retriever import SemanticRetriever


def make_retrieved_chunk(
    chunk_id: str,
    text: str,
    *,
    retrieval_source: str,
    score: float,
    rank: int = 1,
) -> RetrievedChunk:
    chunk = Chunk(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        text=text,
        position=rank,
        start_offset=0,
        end_offset=len(text),
        section_title="Section",
        metadata={"source": "fixture", "source_type": "text", "document_title": f"Doc {chunk_id}"},
    )
    return RetrievedChunk(
        chunk=chunk,
        retrieval_source=retrieval_source,
        score=score,
        rank=rank,
        document_title=f"Doc {chunk_id}",
        document_source="fixture",
    )


class StubEmbedder:
    def __init__(self) -> None:
        self.seen_queries: list[str] = []

    def embed_query(self, query_text: str) -> list[float]:
        self.seen_queries.append(query_text)
        return [0.1, 0.9]


class StubVectorStore:
    def __init__(self, results: list[RetrievedChunk]) -> None:
        self.results = results
        self.last_top_k: int | None = None
        self.last_filters: dict[str, object] | None = None

    def similarity_search(self, query_embedding, *, top_k: int, filters=None):
        self.last_top_k = top_k
        self.last_filters = filters
        return self.results[:top_k]


class StubKeywordStore:
    def __init__(self, results: list[RetrievedChunk]) -> None:
        self.results = results
        self.last_top_k: int | None = None
        self.last_filters: dict[str, object] | None = None

    def keyword_search(self, query_text, *, top_k: int, filters=None):
        self.last_top_k = top_k
        self.last_filters = filters
        return self.results[:top_k]


class StubRetriever:
    def __init__(self, results: list[RetrievedChunk]) -> None:
        self.results = results

    def retrieve(self, query: Query) -> list[RetrievedChunk]:
        return list(self.results)


class UnavailableReranker:
    def is_available(self) -> bool:
        return False


class StubCrossEncoderModel:
    def predict(self, pairs: list[list[str]]) -> list[float]:
        scores: list[float] = []
        for _, text in pairs:
            if "orange" in text:
                scores.append(0.95)
            elif "banana" in text:
                scores.append(0.70)
            else:
                scores.append(0.10)
        return scores


class RetrievalUnitTests(unittest.TestCase):
    def test_semantic_retriever_marks_provenance_and_respects_default_top_k(self) -> None:
        results = [make_retrieved_chunk("a", "alpha", retrieval_source="semantic", score=0.8)]
        retriever = SemanticRetriever(embedder=StubEmbedder(), vector_store=StubVectorStore(results))
        query = Query(query_text="alpha", top_k=5, filters={"document_id": "doc-a"})

        output = retriever.retrieve(query)

        self.assertEqual(len(output), 1)
        self.assertEqual(output[0].retrieval_source, "semantic")
        self.assertEqual(output[0].raw_scores["semantic_rank"], 1.0)
        self.assertEqual(retriever.vector_store.last_top_k, 10)
        self.assertEqual(retriever.vector_store.last_filters, {"document_id": "doc-a"})

    def test_keyword_retriever_marks_provenance_and_respects_default_top_k(self) -> None:
        results = [make_retrieved_chunk("b", "banana", retrieval_source="keyword", score=2.4)]
        retriever = KeywordRetriever(keyword_store=StubKeywordStore(results))

        output = retriever.retrieve(Query(query_text="banana", top_k=5))

        self.assertEqual(output[0].retrieval_source, "keyword")
        self.assertEqual(output[0].raw_scores["keyword_score"], 2.4)
        self.assertEqual(retriever.keyword_store.last_top_k, 10)

    def test_rrf_fusion_deduplicates_by_chunk_id_and_preserves_distinct_ids_with_same_text(self) -> None:
        semantic = [
            make_retrieved_chunk("a", "same text", retrieval_source="semantic", score=0.9, rank=1),
            make_retrieved_chunk("b", "banana orange", retrieval_source="semantic", score=0.8, rank=2),
        ]
        keyword = [
            make_retrieved_chunk("b", "banana orange", retrieval_source="keyword", score=3.2, rank=1),
            make_retrieved_chunk("c", "same text", retrieval_source="keyword", score=2.0, rank=2),
        ]

        fused = reciprocal_rank_fusion(semantic, keyword, top_k=10)

        self.assertEqual([item.chunk.chunk_id for item in fused], ["b", "a", "c"])
        self.assertEqual(fused[0].retrieval_source, "keyword+semantic")
        self.assertIn("rrf_score", fused[0].raw_scores)
        self.assertEqual(len(fused), 3)

    def test_cross_encoder_reranker_reorders_candidates_by_score(self) -> None:
        candidates = [
            make_retrieved_chunk("a", "banana text", retrieval_source="semantic", score=0.5),
            make_retrieved_chunk("b", "orange text", retrieval_source="keyword+semantic", score=0.4),
            make_retrieved_chunk("c", "plain text", retrieval_source="keyword", score=0.3),
        ]
        reranker = CrossEncoderReranker(model=StubCrossEncoderModel())

        reranked = reranker.rerank(Query(query_text="fruit", top_k=5), candidates, top_k=2)

        self.assertEqual([item.chunk.chunk_id for item in reranked], ["b", "a"])
        self.assertEqual(reranked[0].raw_scores["pre_rerank_score"], 0.4)
        self.assertEqual(reranked[0].raw_scores["reranker_score"], 0.95)

    def test_retrieval_pipeline_falls_back_to_fused_results_when_reranker_unavailable(self) -> None:
        candidates = [
            make_retrieved_chunk("a", "alpha", retrieval_source="semantic", score=0.6, rank=1),
            make_retrieved_chunk("b", "beta", retrieval_source="keyword", score=0.5, rank=2),
            make_retrieved_chunk("c", "gamma", retrieval_source="keyword+semantic", score=0.4, rank=3),
        ]
        pipeline = RetrievalPipeline(retriever=StubRetriever(candidates), reranker=UnavailableReranker())

        output = pipeline.retrieve(Query(query_text="test", top_k=2))

        self.assertEqual([item.chunk.chunk_id for item in output], ["a", "b"])
        self.assertEqual(output[0].raw_scores["fallback_to_fused"], 1.0)
        self.assertEqual(output[0].rank, 1)


if __name__ == "__main__":
    unittest.main()
