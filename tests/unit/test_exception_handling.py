from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.llm_adapter import LocalFallbackAdapter
from app.controllers.search_controller import SearchController
from app.models.domain import SearchResult
from app.services.answer_service import AnswerService
from app.services.file_validator import FileValidator, ValidationError
from app.services.report_service import ReportService
from app.utils.exceptions import ReportExportError


def test_validator_rejects_corrupt_pdf(local_tmp_path: Path, monkeypatch):
    path = local_tmp_path / "corrupt.pdf"
    path.write_bytes(b"%PDF-1.4\nnot a real pdf")

    monkeypatch.setattr(
        "app.services.file_validator.detect_mime_type",
        lambda file_path, original_name: ("application/pdf", True),
    )

    with pytest.raises(ValidationError, match="PDF cannot be opened"):
        FileValidator().validate(path, path.name)


def test_validator_rejects_corrupt_image(local_tmp_path: Path, monkeypatch):
    path = local_tmp_path / "corrupt.png"
    path.write_bytes(b"not a real png")

    monkeypatch.setattr(
        "app.services.file_validator.detect_mime_type",
        lambda file_path, original_name: ("image/png", True),
    )

    with pytest.raises(ValidationError, match="Image cannot be opened"):
        FileValidator().validate(path, path.name)


def test_validator_rejects_audio_with_unreadable_metadata(local_tmp_path: Path, monkeypatch):
    path = local_tmp_path / "broken.mp3"
    path.write_bytes(b"ID3 broken audio")

    monkeypatch.setattr(
        "app.services.file_validator.detect_mime_type",
        lambda file_path, original_name: ("audio/mpeg", True),
    )
    monkeypatch.setattr("app.services.file_validator._get_audio_duration_sec", lambda file_path: None)

    with pytest.raises(ValidationError, match="Audio metadata could not be read"):
        FileValidator().validate(path, path.name)


def test_query_rejects_only_stopwords_or_symbols():
    with pytest.raises(ValueError, match="meaningful alphanumeric"):
        SearchController._validate_query_limits("the and or ???", top_k=5)


def test_answer_reports_insufficient_evidence_when_chunks_are_too_low_confidence():
    answer = AnswerService(LocalFallbackAdapter()).answer(
        "What are the requirements?",
        [
            SearchResult(
                chunk_text="Possibly relevant text",
                score=0.9,
                confidence=0.1,
                file_id="f1",
                chunk_index=0,
            )
        ],
    )

    assert answer.insufficient_evidence is True
    assert answer.supporting_chunks == []


def test_report_export_rejects_empty_content(local_tmp_path: Path):
    service = ReportService(reports_dir=local_tmp_path / "reports")

    with pytest.raises(ReportExportError, match="empty report"):
        service.write_text_report("report.txt", "")
