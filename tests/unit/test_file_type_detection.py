from __future__ import annotations

from pathlib import Path

from app.models.domain import FileType
from app.services.file_type_detector import resolve_file_type
from app.services.file_validator import FileValidator, ValidationError


def test_resolve_file_type_uses_mime_category():
    assert resolve_file_type("application/pdf") == FileType.PDF
    assert resolve_file_type("image/png") == FileType.IMAGE
    assert resolve_file_type("audio/mpeg") == FileType.AUDIO


def test_validator_accepts_supported_content_even_with_wrong_extension(
    local_tmp_path: Path,
    monkeypatch,
):
    path = local_tmp_path / "document.bin"
    path.write_bytes(b"%PDF-1.4\n% fake but enough for this unit test\n")

    monkeypatch.setattr(
        "app.services.file_validator.detect_mime_type",
        lambda file_path, original_name: ("application/pdf", True),
    )
    monkeypatch.setattr("app.services.file_validator.FileValidator._check_pdf_page_count", lambda self, file_path: None)

    FileValidator().validate(path, path.name)


def test_validator_rejects_unsupported_content(local_tmp_path: Path, monkeypatch):
    path = local_tmp_path / "notes.pdf"
    path.write_text("plain text, not a supported binary type", encoding="utf-8")

    monkeypatch.setattr(
        "app.services.file_validator.detect_mime_type",
        lambda file_path, original_name: ("text/plain", True),
    )

    try:
        FileValidator().validate(path, path.name)
    except ValidationError as exc:
        assert "Unsupported file MIME type" in str(exc)
    else:
        raise AssertionError("Expected unsupported content to be rejected")


def test_validator_rejects_audio_over_duration_limit(local_tmp_path: Path, monkeypatch):
    path = local_tmp_path / "long.mp3"
    path.write_bytes(b"ID3 fake audio")

    monkeypatch.setattr(
        "app.services.file_validator.detect_mime_type",
        lambda file_path, original_name: ("audio/mpeg", True),
    )
    monkeypatch.setattr("app.services.file_validator._get_audio_duration_sec", lambda file_path: 601.0)
    monkeypatch.setattr("app.services.file_validator.settings.max_audio_duration_sec", 600)

    try:
        FileValidator().validate(path, path.name)
    except ValidationError as exc:
        assert "Audio is too long" in str(exc)
    else:
        raise AssertionError("Expected overlong audio to be rejected")
