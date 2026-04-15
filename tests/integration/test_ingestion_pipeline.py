from __future__ import annotations

import gc
import shutil
import tempfile
import unittest
from pathlib import Path

from src.core.models import Document
from src.ingestion.chunkers.contextual_chunker import ContextualChunker
from src.ingestion.embedders.sentence_transformer_embedder import SentenceTransformerEmbedder
from src.ingestion.loaders.text_loader import TextLoader
from src.ingestion.pipeline import IngestionPipeline
from src.storage.keyword_stores.bm25_store import BM25KeywordStore
from src.storage.metadata_store import MetadataStore
from src.storage.vector_stores.chroma_store import ChromaVectorStore


class StubModel:
    def encode(self, texts, batch_size, convert_to_numpy, show_progress_bar, normalize_embeddings):
        return [[float(len(text)), float(index + 1)] for index, text in enumerate(texts)]


class PipelineTests(unittest.TestCase):
    def test_reingestion_replaces_prior_artifacts_for_same_document_id(self) -> None:
        temp_dir = tempfile.mkdtemp()
        pipeline = None
        try:
            source_path = Path(temp_dir) / "source.txt"
            source_path.write_text("Original paragraph.\n\nSecond paragraph.", encoding="utf-8")

            pipeline = IngestionPipeline(
                loaders={"text": TextLoader()},
                chunker=ContextualChunker(chunk_size=64, overlap=10),
                embedder=SentenceTransformerEmbedder(model=StubModel()),
                vector_store=ChromaVectorStore(
                    persist_directory=str(Path(temp_dir) / "vector_db"),
                    collection_name="pipeline_chunks",
                ),
                keyword_store=BM25KeywordStore(persist_directory=str(Path(temp_dir) / "keyword_index")),
                metadata_store=MetadataStore(storage_path=str(Path(temp_dir) / "processed" / "metadata.json")),
            )

            first_result = pipeline.ingest_source(str(source_path), "text")
            source_path.write_text("Replacement paragraph with different wording.", encoding="utf-8")
            second_result = pipeline.ingest_source(str(source_path), "text")

            self.assertEqual(first_result.document.document_id, second_result.document.document_id)
            self.assertEqual(pipeline.metadata_store.get_document(second_result.document.document_id).content, second_result.document.content)

            keyword_hits = pipeline.keyword_store.keyword_search("Replacement", top_k=5)
            self.assertTrue(keyword_hits)
            self.assertTrue(all(hit.chunk.document_id == second_result.document.document_id for hit in keyword_hits))
            self.assertEqual(pipeline.vector_store._collection.count(), len(second_result.chunks))
        finally:
            pipeline = None
            gc.collect()
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
