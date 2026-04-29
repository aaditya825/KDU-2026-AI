from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.llm_adapter import LocalFallbackAdapter
from app.controllers.file_controller import FileController
from app.controllers.processing_controller import ProcessingController
from app.controllers.search_controller import SearchController
from app.models.domain import ExtractionMethod, ExtractionResult, SearchResult, TextChunk
from app.repositories.file_repository import FileRepository
from app.repositories.processing_repository import ProcessingRepository
from app.services.answer_service import AnswerService
from app.services.post_processor import PostProcessor
from app.services.search_service import SearchService


class FakePipeline:
    def process(self, file_path: str) -> ExtractionResult:
        return ExtractionResult(
            raw_text=(
                "[PAGE 1]\nRevenue grew by 20 percent in 2025 while gross margin "
                "improved and operating efficiency increased across teams."
            ),
            confidence=0.95,
            method=ExtractionMethod.DIRECT_TEXT,
            page_metadata=[{"page": 1, "method": "direct_text"}],
            warnings=[],
            latency_ms=10,
        )


class FakeRouter:
    def get_pipeline(self, meta):
        return FakePipeline()


class FakeEmbedding:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t))] for t in texts]

    def embed_query(self, query: str) -> list[float]:
        return [float(len(query))]


class FakeVectorStore:
    def __init__(self) -> None:
        self._chunks: dict[str, list[TextChunk]] = {}

    def add_chunks(self, chunks, embeddings, file_id):
        self._chunks[file_id] = chunks

    def search(self, file_id, query_embedding, top_k=5):
        chunks = self._chunks.get(file_id, [])
        return [
            SearchResult(
                chunk_text=c.text,
                score=0.85,
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


@pytest.mark.integration
def test_phase1_to_phase3_backend_flow(local_tmp_path: Path, monkeypatch):
    from app.config.settings import settings

    monkeypatch.setattr(settings, "data_dir", local_tmp_path / "data")
    monkeypatch.setattr(settings, "sqlite_db_path", local_tmp_path / "data/sqlite/cas.db")
    settings.ensure_dirs()

    # Create a valid small PDF for ingestion.
    try:
        import fitz  # type: ignore
    except Exception:
        pytest.skip("PyMuPDF unavailable in test environment")

    pdf_path = local_tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Revenue report")
    doc.save(str(pdf_path))
    doc.close()

    file_controller = FileController()
    meta = file_controller.ingest_file(str(pdf_path))

    file_repo = FileRepository()
    proc_repo = ProcessingRepository()
    processing_controller = ProcessingController(
        file_repo=file_repo,
        proc_repo=proc_repo,
        router=FakeRouter(),
        post_processor=PostProcessor(LocalFallbackAdapter()),
    )
    process_result = processing_controller.process_file(meta.file_id)
    assert process_result.cleaned_text

    search_service = SearchService(FakeEmbedding(), FakeVectorStore())
    answer_service = AnswerService(LocalFallbackAdapter())
    search_controller = SearchController(
        file_repo=file_repo,
        proc_repo=proc_repo,
        search_service=search_service,
        answer_service=answer_service,
    )

    hits = search_controller.search(meta.file_id, "revenue growth", top_k=3)
    assert hits
    answer = search_controller.answer(meta.file_id, "What grew?", top_k=3)
    assert answer.answer
