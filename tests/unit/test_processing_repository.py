from __future__ import annotations

from pathlib import Path

from app.models.domain import ExtractionMethod, ExtractionResult, ProcessingResult
from app.repositories.file_repository import FileRepository
from app.repositories.processing_repository import ProcessingRepository


def test_processing_repository_persists_latency_warnings_and_page_metadata(local_tmp_path: Path):
    db_path = local_tmp_path / "cas_test.db"
    FileRepository(db_path=db_path)  # initializes schema + migrations
    repo = ProcessingRepository(db_path=db_path)

    result = ProcessingResult(
        file_id="file-123",
        cleaned_text="clean text",
        summary="sum",
        key_points=["a", "b"],
        topic_tags=["x", "y"],
        latency_ms=321,
        error_message="",
        extraction=ExtractionResult(
            raw_text="raw",
            confidence=0.67,
            method=ExtractionMethod.OCR,
            page_metadata=[{"page": 1, "method": "ocr"}],
            warnings=["low confidence page"],
            latency_ms=123,
        ),
    )

    # Need a file row because processed_outputs has FK to files.
    file_repo = FileRepository(db_path=db_path)
    from app.models.domain import FileMetadata, FileStatus, FileType

    file_repo.insert(
        FileMetadata(
            file_id="file-123",
            original_name="sample.pdf",
            stored_path=str(local_tmp_path / "sample.pdf"),
            file_type=FileType.PDF,
            mime_type="application/pdf",
            size_bytes=100,
            status=FileStatus.UPLOADED,
        )
    )

    repo.save_processing_result(result)
    row = repo.get_processing_result("file-123")
    assert row is not None
    assert row["latency_ms"] == 321
    assert row["extraction_latency_ms"] == 123
    assert row["warnings"] == ["low confidence page"]
    assert row["page_metadata"] == [{"page": 1, "method": "ocr"}]
