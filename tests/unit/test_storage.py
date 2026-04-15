from __future__ import annotations

import gc
import shutil
import tempfile
import unittest
from pathlib import Path

from src.core.models import Chunk, Document
from src.storage.keyword_stores.bm25_store import BM25KeywordStore
from src.storage.metadata_store import MetadataStore
from src.storage.vector_stores.chroma_store import ChromaVectorStore


def make_chunk(chunk_id: str, document_id: str, text: str, position: int) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id=document_id,
        text=text,
        position=position,
        start_offset=0,
        end_offset=len(text),
        section_title="Section",
        metadata={
            "source": "fixture",
            "source_type": "text",
            "document_title": f"Doc {document_id}",
        },
    )


class StorageTests(unittest.TestCase):
    def test_bm25_store_persists_and_reloads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = BM25KeywordStore(persist_directory=temp_dir)
            store.upsert(
                [
                    make_chunk("chunk-1", "doc-1", "hybrid search retrieves concepts and keywords", 1),
                    make_chunk("chunk-2", "doc-2", "another document about databases", 1),
                ]
            )

            reloaded = BM25KeywordStore(persist_directory=temp_dir)
            results = reloaded.keyword_search("keywords", top_k=2)

            self.assertEqual(results[0].chunk.chunk_id, "chunk-1")
            self.assertTrue((Path(temp_dir) / "bm25_index.json").exists())

    def test_bm25_prefers_summary_fact_chunk_for_exact_fact_query(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = BM25KeywordStore(persist_directory=temp_dir)
            store.upsert(
                [
                    Chunk(
                        chunk_id="summary",
                        document_id="doc-1",
                        text="Publisher: Marvel Comics\nFirst appearance: Amazing Fantasy #15 (August 1962)",
                        position=1,
                        start_offset=0,
                        end_offset=78,
                        section_title="Summary facts",
                        metadata={
                            "source": "fixture",
                            "source_type": "url",
                            "document_title": "Spider-Man",
                            "section_type": "infobox",
                        },
                    ),
                    Chunk(
                        chunk_id="body",
                        document_id="doc-1",
                        text="Spider-Man appears in many comics and later series including The Amazing Spider-Man.",
                        position=2,
                        start_offset=79,
                        end_offset=160,
                        section_title="Publication history",
                        metadata={
                            "source": "fixture",
                            "source_type": "url",
                            "document_title": "Spider-Man",
                        },
                    ),
                ]
            )

            results = store.keyword_search("What is Spider-Man's first appearance?", top_k=2)

            self.assertEqual(results[0].chunk.chunk_id, "summary")

    def test_chroma_store_persists_and_replaces_document_vectors(self) -> None:
        temp_dir = tempfile.mkdtemp()
        store = None
        reloaded = None
        try:
            store = ChromaVectorStore(persist_directory=temp_dir, collection_name="test_chunks")
            chunk = make_chunk("chunk-1", "doc-1", "semantic retrieval text", 1)
            store.upsert([chunk], [[1.0, 0.0]])

            reloaded = ChromaVectorStore(persist_directory=temp_dir, collection_name="test_chunks")
            results = reloaded.similarity_search([1.0, 0.0], top_k=1)
            self.assertEqual(results[0].chunk.chunk_id, "chunk-1")

            reloaded.delete_document("doc-1")
            replacement = make_chunk("chunk-2", "doc-1", "replacement text", 1)
            reloaded.upsert([replacement], [[0.0, 1.0]])
            after_replace = reloaded.similarity_search([0.0, 1.0], top_k=5)
            self.assertEqual([item.chunk.chunk_id for item in after_replace], ["chunk-2"])
        finally:
            store = None
            reloaded = None
            gc.collect()
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_metadata_store_persists_documents_and_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "metadata.json"
            document = Document(
                document_id="doc-1",
                source_type="pdf",
                source="fixture.pdf",
                title="Fixture",
                content="fixture content",
                metadata={"source": "fixture.pdf", "source_type": "pdf", "document_title": "Fixture"},
            )
            chunks = [make_chunk("chunk-1", "doc-1", "fixture content", 1)]
            store = MetadataStore(storage_path=str(path))
            store.upsert_document(document, chunks)

            reloaded = MetadataStore(storage_path=str(path))
            self.assertEqual(reloaded.get_document("doc-1").title, "Fixture")
            self.assertEqual(reloaded.get_chunks("doc-1")[0].chunk_id, "chunk-1")


if __name__ == "__main__":
    unittest.main()
