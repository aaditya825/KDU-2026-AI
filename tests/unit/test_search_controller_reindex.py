from __future__ import annotations

from dataclasses import dataclass

from app.controllers.search_controller import SearchController
from app.models.domain import FileMetadata, FileStatus, FileType, SearchResult, TextChunk
from app.services.answer_service import AnswerService
from app.services.search_service import SearchService
from app.adapters.llm_adapter import LocalFallbackAdapter


class FakeEmbedding:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t))] for t in texts]

    def embed_query(self, query: str) -> list[float]:
        return [float(len(query))]


class FakeVectorStore:
    def __init__(self) -> None:
        self.add_calls = 0
        self._chunks: dict[str, list[TextChunk]] = {}

    def add_chunks(self, chunks, embeddings, file_id):
        self.add_calls += 1
        self._chunks[file_id] = chunks

    def search(self, file_id, query_embedding, top_k=5):
        chunks = self._chunks.get(file_id, [])
        return [
            SearchResult(
                chunk_text=c.text,
                score=0.9,
                file_id=file_id,
                file_name=c.metadata.get("file_name", ""),
                chunk_index=c.chunk_index,
                confidence=c.confidence,
                source_metadata=c.metadata,
            )
            for c in chunks[:top_k]
        ]

    def delete_file(self, file_id: str) -> None:
        self._chunks.pop(file_id, None)

    def count(self, file_id: str) -> int:
        return len(self._chunks.get(file_id, []))


@dataclass
class FakeFileRepo:
    def get(self, file_id: str):
        return FileMetadata(
            file_id=file_id,
            original_name="doc.pdf",
            stored_path="unused",
            file_type=FileType.PDF,
            mime_type="application/pdf",
            size_bytes=100,
            status=FileStatus.COMPLETED,
        )


class FakeProcRepo:
    def get_chunks(self, file_id: str):
        return [
            TextChunk(
                chunk_id="c1",
                file_id=file_id,
                chunk_index=0,
                text="[PAGE 1] revenue increased",
                confidence=0.9,
                metadata={"file_name": "doc.pdf", "pages": [1], "chunk_index": 0},
            )
        ]

    def get_processing_result(self, file_id: str):
        raise AssertionError("should not be called when DB chunks already exist")

    def save_chunks(self, chunks):
        return None


def test_reindex_when_chunks_exist_but_vector_store_missing():
    fake_embed = FakeEmbedding()
    fake_store = FakeVectorStore()
    search_svc = SearchService(fake_embed, fake_store)
    answer_svc = AnswerService(LocalFallbackAdapter())

    controller = SearchController(
        file_repo=FakeFileRepo(),
        proc_repo=FakeProcRepo(),
        search_service=search_svc,
        answer_service=answer_svc,
    )

    results = controller.search("file-1", "revenue", top_k=3)
    assert fake_store.add_calls == 1
    assert results


def test_search_rejects_top_k_above_limit():
    fake_embed = FakeEmbedding()
    fake_store = FakeVectorStore()
    search_svc = SearchService(fake_embed, fake_store)
    answer_svc = AnswerService(LocalFallbackAdapter())

    controller = SearchController(
        file_repo=FakeFileRepo(),
        proc_repo=FakeProcRepo(),
        search_service=search_svc,
        answer_service=answer_svc,
    )

    try:
        controller.search("file-1", "revenue", top_k=999)
    except ValueError as exc:
        assert "top_k must be between" in str(exc)
    else:
        raise AssertionError("Expected high top_k to be rejected")
