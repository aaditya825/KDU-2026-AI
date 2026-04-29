"""
Local file storage for ingested files.

Storage copies the validated source file into the controlled uploads directory
and records MIME/file type using content-based detection.
"""

from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

from app.config.settings import settings
from app.models.domain import FileMetadata, FileStatus
from app.services.file_type_detector import detect_mime_type, resolve_file_type
from app.utils.logging_utils import get_logger
from app.utils.timing import Timer

log = get_logger(__name__)


def _sanitise_filename(name: str) -> str:
    """
    Return a safe filename:
    - strip directory components
    - replace unsafe characters
    - cap length
    """
    name = Path(name).name
    name = re.sub(r"[^\w.\-]", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_.")
    return name[:200] or "file"


class FileStorage:
    """Handles persisting uploaded files to local disk."""

    def __init__(self) -> None:
        settings.ensure_dirs()
        self._uploads_dir = settings.uploads_dir

    def save(self, source_path: Path, original_name: str) -> FileMetadata:
        """
        Copy *source_path* into uploads and return persisted file metadata.
        """
        with Timer("file_storage.save") as t:
            file_id = str(uuid.uuid4())
            safe_name = _sanitise_filename(original_name)
            dest_filename = f"{file_id}_{safe_name}"
            dest_path = self._uploads_dir / dest_filename

            shutil.copy2(source_path, dest_path)
            size_bytes = dest_path.stat().st_size

            mime_type, detected_from_content = detect_mime_type(dest_path, original_name)
            file_type = resolve_file_type(mime_type)

        log.info(
            "File saved",
            extra={
                "file_id": file_id,
                "original_name": original_name,
                "dest_path": str(dest_path),
                "size_bytes": size_bytes,
                "mime_type": mime_type,
                "detected_from_content": detected_from_content,
                "file_type": file_type.value,
                "latency_ms": t.elapsed_ms,
            },
        )

        return FileMetadata(
            file_id=file_id,
            original_name=original_name,
            stored_path=str(dest_path),
            file_type=file_type,
            mime_type=mime_type,
            size_bytes=size_bytes,
            status=FileStatus.UPLOADED,
        )
