"""
app/controllers/file_controller.py
────────────────────────────────────
Orchestrates the Phase-1 ingest flow:
    validate → save to storage → persist metadata → return FileMetadata
"""

from __future__ import annotations

from pathlib import Path

from app.models.domain import FileMetadata
from app.repositories.file_repository import FileRepository
from app.services.file_validator import FileValidator
from app.storage.file_storage import FileStorage
from app.utils.logging_utils import get_logger
from app.utils.timing import Timer

log = get_logger(__name__)


class FileController:
    """Entry point for CLI and (later) Streamlit upload flows."""

    def __init__(
        self,
        validator: FileValidator | None = None,
        storage: FileStorage | None = None,
        repository: FileRepository | None = None,
    ) -> None:
        self._validator = validator or FileValidator()
        self._storage = storage or FileStorage()
        self._repository = repository or FileRepository()

    def ingest_file(self, path: str | Path) -> FileMetadata:
        """
        Validate, store, and persist a single file.

        Parameters
        ----------
        path:
            Path to the file to ingest.

        Returns
        -------
        FileMetadata
            Fully populated metadata with status=UPLOADED.

        Raises
        ------
        app.services.file_validator.ValidationError
            If the file fails any validation check.
        """
        source = Path(path).expanduser().resolve()
        original_name = source.name

        log.info("Ingest started", extra={"path": str(source)})

        with Timer("file_controller.ingest") as t:
            # 1. Validate before touching storage
            self._validator.validate(source, original_name)

            # 2. Copy to uploads dir and build FileMetadata
            meta = self._storage.save(source, original_name)

            # 3. Persist to SQLite
            self._repository.insert(meta)

        log.info(
            "Ingest complete",
            extra={
                "file_id": meta.file_id,
                "file_type": meta.file_type.value,
                "status": meta.status.value,
                "latency_ms": t.elapsed_ms,
            },
        )
        return meta
