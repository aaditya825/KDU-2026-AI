from __future__ import annotations

import gc
import shutil
import tempfile
import unittest
from pathlib import Path

from src.core.models import Chunk, Query
from src.retrieval.pipeline import RetrievalPipeline
from src.retrieval.rerankers.cross_encoder_reranker import CrossEncoderReranker
from src.retrieval.retrievers.hybrid_retriever import HybridRetriever
from src.retrieval.retrievers.keyword_retriever import KeywordRetriever
from src.retrieval.retrievers.semantic_retriever import SemanticRetriever
from src.storage.keyword_stores.bm25_store import BM25KeywordStore
from src.storage.vector_stores.chroma_store import ChromaVectorStore


class StubEmbedder:
    def __init__(self, query_vector: list[float]) -> None:
        self.query_vector = query_vector

    def embed_query(self, query_text: str) -> list[float]:
        return list(self.query_vector)


class StubCrossEncoderModel:
    def predict(self, pairs: list[list[str]]) -> list[float]:
        scores: list[float] = []
        for _, text in pairs:
            if "orange" in text:
                scores.append(0.99)
            elif "banana" in text:
                scores.append(0.70)
            else:
                scores.append(0.10)
        return scores


def make_chunk(chunk_id: str, document_id: str, text: str, position: int) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id=document_id,
        text=text,
        position=position,
        start_offset=0,
        end_offset=len(text),
        section_title="Section",
        metadata={"source": "fixture", "source_type": "text", "document_title": document_id},
    )


class RetrievalPipelineIntegrationTests(unittest.TestCase):
    def test_retrieval_pipeline_fuses_and_reranks_real_store_results(self) -> None:
        temp_dir = tempfile.mkdtemp()
        vector_store = None
        keyword_store = None
        try:
            vector_store = ChromaVectorStore(
                persist_directory=str(Path(temp_dir) / "vector_db"),
                collection_name="retrieval_pipeline",
            )
            keyword_store = BM25KeywordStore(persist_directory=str(Path(temp_dir) / "keyword_index"))

            chunks = [
                make_chunk("chunk-1", "doc-1", "banana concept overview", 1),
                make_chunk("chunk-2", "doc-2", "banana orange exact keyword match", 1),
                make_chunk("chunk-3", "doc-3", "grape unrelated passage", 1),
            ]
            embeddings = [
                [1.0, 0.0],
                [0.8, 0.2],
                [0.0, 1.0],
            ]
            vector_store.upsert(chunks, embeddings)
            keyword_store.upsert(chunks)

            semantic = SemanticRetriever(
                embedder=StubEmbedder([1.0, 0.0]),
                vector_store=vector_store,
            )
            keyword = KeywordRetriever(keyword_store=keyword_store)
            hybrid = HybridRetriever(semantic_retriever=semantic, keyword_retriever=keyword)
            pipeline = RetrievalPipeline(
                retriever=hybrid,
                reranker=CrossEncoderReranker(model=StubCrossEncoderModel()),
            )

            results = pipeline.retrieve(Query(query_text="banana orange", top_k=5))

            self.assertEqual([item.chunk.chunk_id for item in results[:3]], ["chunk-2", "chunk-1", "chunk-3"])
            self.assertIn("reranker_score", results[0].raw_scores)
            self.assertIn("rrf_score", results[0].raw_scores)
            self.assertEqual(results[0].retrieval_source, "keyword+semantic|reranked")
        finally:
            vector_store = None
            keyword_store = None
            gc.collect()
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
