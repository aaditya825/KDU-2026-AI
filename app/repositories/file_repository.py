"""
app/repositories/file_repository.py
─────────────────────────────────────
SQLite-backed persistence for file metadata.

Schema
------
  files             -- one row per uploaded file (FileMetadata)
  processed_outputs -- populated in Phase 2
  chunks            -- populated in Phase 3
  model_metrics     -- populated in Phase 2/3
"""

from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path
from typing import Optional

from app.config.settings import settings
from app.models.domain import FileMetadata, FileStatus, FileType
from app.utils.logging_utils import get_logger

log = get_logger(__name__)

_FALLBACK_DB = Path("data/sqlite/cas_fallback.db")

_CREATE_FILES_TABLE = """
CREATE TABLE IF NOT EXISTS files (
    file_id       TEXT PRIMARY KEY,
    original_name TEXT NOT NULL,
    stored_path   TEXT NOT NULL,
    file_type     TEXT NOT NULL,
    mime_type     TEXT NOT NULL,
    size_bytes    INTEGER NOT NULL,
    status        TEXT NOT NULL DEFAULT 'uploaded',
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
"""

_CREATE_PROCESSED_TABLE = """
CREATE TABLE IF NOT EXISTS processed_outputs (
    output_id        TEXT PRIMARY KEY,
    file_id          TEXT NOT NULL REFERENCES files(file_id),
    raw_text         TEXT,
    cleaned_text     TEXT,
    summary          TEXT,
    key_points       TEXT,
    topic_tags       TEXT,
    extraction_method TEXT,
    confidence       REAL,
    model_config_id  TEXT,
    created_at       TEXT NOT NULL,
    page_metadata    TEXT,
    latency_ms       INTEGER,
    extraction_latency_ms INTEGER,
    warnings         TEXT,
    error_message    TEXT
);
"""

_CREATE_CHUNKS_TABLE = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id    TEXT PRIMARY KEY,
    file_id     TEXT NOT NULL REFERENCES files(file_id),
    chunk_index INTEGER NOT NULL,
    text        TEXT NOT NULL,
    confidence  REAL,
    metadata    TEXT,
    vector_ref  TEXT
);
"""

_CREATE_METRICS_TABLE = """
CREATE TABLE IF NOT EXISTS model_metrics (
    metric_id       TEXT PRIMARY KEY,
    file_id         TEXT NOT NULL REFERENCES files(file_id),
    stage           TEXT NOT NULL,
    model_name      TEXT,
    provider        TEXT,
    latency_ms      INTEGER,
    estimated_cost  REAL,
    status          TEXT DEFAULT 'success',
    error_message   TEXT
);
"""


def _can_use_sqlite(path: Path) -> bool:
    probe = path.parent / ".sqlite_probe_tmp.db"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(probe))
        conn.execute("CREATE TABLE IF NOT EXISTS _probe (x INTEGER)")
        conn.execute("INSERT INTO _probe VALUES (1)")
        conn.commit()
        conn.close()
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        probe.unlink(missing_ok=True)
        return False


def resolve_sqlite_db_path(configured: Optional[Path] = None) -> Path:
    target = configured or settings.sqlite_db_path
    if _can_use_sqlite(target):
        return target

    fallback = _FALLBACK_DB
    fallback.parent.mkdir(parents=True, exist_ok=True)
    if _can_use_sqlite(fallback):
        log.warning(
            "Configured SQLite path blocks writes; falling back to %s for this session.",
            fallback,
        )
        return fallback
    raise RuntimeError(
        f"Unable to open writable SQLite database at '{target}' or fallback '{fallback}'."
    )


class FileRepository:
    """CRUD operations for the files table and schema initialisation."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = resolve_sqlite_db_path(db_path)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=DELETE;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(_CREATE_FILES_TABLE)
            conn.execute(_CREATE_PROCESSED_TABLE)
            conn.execute(_CREATE_CHUNKS_TABLE)
            conn.execute(_CREATE_METRICS_TABLE)
            self._migrate_processed_outputs(conn)
        log.debug("SQLite schema initialised", extra={"db": str(self._db_path)})

    @staticmethod
    def _migrate_processed_outputs(conn: sqlite3.Connection) -> None:
        existing = {
            row["name"] for row in conn.execute("PRAGMA table_info(processed_outputs)").fetchall()
        }
        required: dict[str, str] = {
            "page_metadata": "TEXT",
            "latency_ms": "INTEGER",
            "extraction_latency_ms": "INTEGER",
            "warnings": "TEXT",
            "error_message": "TEXT",
        }
        for col, col_type in required.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE processed_outputs ADD COLUMN {col} {col_type}")

    def insert(self, meta: FileMetadata) -> None:
        now = datetime.datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO files
                    (file_id, original_name, stored_path, file_type, mime_type,
                     size_bytes, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meta.file_id,
                    meta.original_name,
                    meta.stored_path,
                    meta.file_type.value,
                    meta.mime_type,
                    meta.size_bytes,
                    meta.status.value,
                    meta.created_at.isoformat(),
                    now,
                ),
            )
        log.info("File metadata persisted", extra={"file_id": meta.file_id})

    def update_status(self, file_id: str, status: FileStatus) -> None:
        now = datetime.datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE files SET status = ?, updated_at = ? WHERE file_id = ?",
                (status.value, now, file_id),
            )

    def get(self, file_id: str) -> Optional[FileMetadata]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM files WHERE file_id = ?", (file_id,)
            ).fetchone()
        if row is None:
            return None
        return self._row_to_metadata(dict(row))

    def list_all(self) -> list[FileMetadata]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM files ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_metadata(dict(r)) for r in rows]

    @staticmethod
    def _row_to_metadata(row: dict) -> FileMetadata:
        return FileMetadata(
            file_id=row["file_id"],
            original_name=row["original_name"],
            stored_path=row["stored_path"],
            file_type=FileType(row["file_type"]),
            mime_type=row["mime_type"],
            size_bytes=row["size_bytes"],
            status=FileStatus(row["status"]),
            created_at=datetime.datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.datetime.fromisoformat(row["updated_at"]),
        )
