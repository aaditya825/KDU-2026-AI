"""
Content-based file type detection.

Uses libmagic via python-magic when available. Filename extension is only a
fallback for environments where content detection cannot run.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from app.models.domain import FileType

SUPPORTED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/jpg",
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
    }
)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".pdf", ".jpg", ".jpeg", ".png", ".mp3", ".wav"}
)

_EXT_TO_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
}


def detect_mime_type(path: Path, original_name: str | None = None) -> tuple[str, bool]:
    """
    Return ``(mime_type, detected_from_content)``.

    ``detected_from_content`` is False only when falling back to filename-based
    guessing because libmagic is unavailable or failed.
    """
    try:
        import magic  # type: ignore

        detected = magic.from_file(str(path), mime=True) or ""
        if detected:
            return detected, True
    except Exception:
        pass

    name = original_name or path.name
    mime, _ = mimetypes.guess_type(name)
    if mime:
        return mime, False

    ext = Path(name).suffix.lower()
    return _EXT_TO_MIME.get(ext, "application/octet-stream"), False


def resolve_file_type(mime_type: str) -> FileType:
    """Map a MIME type to the internal FileType enum."""
    if mime_type == "application/pdf":
        return FileType.PDF
    if mime_type.startswith("image/") and mime_type in SUPPORTED_MIME_TYPES:
        return FileType.IMAGE
    if mime_type.startswith("audio/") and mime_type in SUPPORTED_MIME_TYPES:
        return FileType.AUDIO
    raise ValueError(
        f"Unsupported file MIME type '{mime_type}'. "
        "Accepted content types: PDF, JPEG/PNG image, MP3/WAV audio."
    )
