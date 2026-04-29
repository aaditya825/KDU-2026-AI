"""
Pre-storage file validation.

Validation is content-first: MIME type is detected from file bytes when
python-magic/libmagic is available. Filename extension is only used as a
fallback when content detection cannot run.
"""

from __future__ import annotations

from pathlib import Path

from app.config.settings import settings
from app.models.domain import FileType
from app.services.file_type_detector import (
    SUPPORTED_EXTENSIONS,
    detect_mime_type,
    resolve_file_type,
)
from app.utils.logging_utils import get_logger

log = get_logger(__name__)


class ValidationError(ValueError):
    """Raised when a file fails any validation check."""


class FileValidator:
    """Validates a file before it is accepted into the system."""

    def __init__(self) -> None:
        self._max_bytes = settings.max_upload_bytes

    def validate(self, path: Path, original_name: str) -> None:
        self._check_exists(path)
        self._check_not_empty(path)
        self._check_size(path)
        file_type = self._check_type(path, original_name)
        self._check_model_safe_limits(path, file_type)

        log.info(
            "File validation passed",
            extra={"path": str(path), "original_name": original_name},
        )

    def _check_exists(self, path: Path) -> None:
        if not path.exists():
            raise ValidationError(f"File does not exist: {path}")

    def _check_not_empty(self, path: Path) -> None:
        if path.stat().st_size == 0:
            raise ValidationError("File is empty (0 bytes). Please upload a non-empty file.")

    def _check_size(self, path: Path) -> None:
        size = path.stat().st_size
        if size > self._max_bytes:
            mb = size / (1024 * 1024)
            raise ValidationError(
                f"File is too large ({mb:.1f} MB). "
                f"Maximum allowed: {settings.max_upload_mb} MB."
            )

    def _check_type(self, path: Path, original_name: str) -> FileType:
        mime_type, from_content = detect_mime_type(path, original_name)
        try:
            return resolve_file_type(mime_type)
        except ValueError as exc:
            if from_content:
                raise ValidationError(str(exc)) from exc

            ext = Path(original_name).suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                raise ValidationError(
                    f"Unsupported file type. Detected MIME '{mime_type}', "
                    f"extension '{ext}'. Accepted extensions: "
                    f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}."
                ) from exc
            return resolve_file_type(mime_type)

    def _check_model_safe_limits(self, path: Path, file_type: FileType) -> None:
        if file_type == FileType.PDF:
            self._check_pdf_page_count(path)
        elif file_type == FileType.IMAGE:
            self._check_image_pixels(path)
        elif file_type == FileType.AUDIO:
            self._check_audio_duration(path)

    def _check_pdf_page_count(self, path: Path) -> None:
        try:
            import fitz

            doc = fitz.open(str(path))
            try:
                page_count = doc.page_count
            finally:
                doc.close()
        except Exception as exc:
            log.warning("Could not inspect PDF page count before processing: %s", exc)
            return

        if page_count > settings.max_pdf_pages:
            raise ValidationError(
                f"PDF has too many pages ({page_count}). "
                f"Maximum allowed before processing: {settings.max_pdf_pages} pages."
            )

    def _check_image_pixels(self, path: Path) -> None:
        try:
            from PIL import Image

            with Image.open(path) as img:
                width, height = img.size
        except Exception as exc:
            log.warning("Could not inspect image dimensions before processing: %s", exc)
            return

        pixels = width * height
        if pixels > settings.max_image_pixels:
            raise ValidationError(
                f"Image is too large ({width}x{height} = {pixels:,} pixels). "
                f"Maximum allowed before processing: {settings.max_image_pixels:,} pixels."
            )

    def _check_audio_duration(self, path: Path) -> None:
        duration = _get_audio_duration_sec(path)
        if duration is None:
            log.warning("Could not inspect audio duration before processing: %s", path)
            return

        if duration > settings.max_audio_duration_sec:
            raise ValidationError(
                f"Audio is too long ({duration:.1f} seconds). "
                f"Maximum allowed before processing: {settings.max_audio_duration_sec} seconds."
            )


def _get_audio_duration_sec(path: Path) -> float | None:
    """Return audio duration in seconds when it can be read cheaply."""
    try:
        from mutagen import File as MutagenFile

        audio = MutagenFile(path)
        if audio is not None and getattr(audio, "info", None) is not None:
            length = getattr(audio.info, "length", None)
            if length is not None:
                return float(length)
    except Exception:
        pass

    if path.suffix.lower() == ".wav":
        try:
            import wave

            with wave.open(str(path), "rb") as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                if rate:
                    return frames / float(rate)
        except Exception:
            pass

    return None
