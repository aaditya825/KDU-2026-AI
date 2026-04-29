"""
app/repositories/processing_repository.py
──────────────────────────────────────────
Persistence for processed outputs, text chunks, and model metrics.

All writes go to the same SQLite database initialised by FileRepository.
This repository assumes the schema was already created (tables exist).
"""

from __future__ import annotations

import datetime
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional

from app.config.settings import settings
from app.repositories.file_repository import resolve_sqlite_db_path
from app.models.domain import (
    ExtractionMethod,
    ProcessingResult,
    TextChunk,
    ModelMetric,
)
from app.utils.logging_utils import get_logger

log = get_logger(__name__)


class ProcessingRepository:
    """Read/write for processed_outputs, chunks, and model_metrics tables."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = resolve_sqlite_db_path(db_path or settings.sqlite_db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=DELETE;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    # ── Processed outputs ──────────────────────────────────────────────────

    def save_processing_result(self, result: ProcessingResult) -> str:
        """Persist a ProcessingResult; returns the generated output_id."""
        output_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()

        extraction = result.extraction
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO processed_outputs
                    (output_id, file_id, raw_text, cleaned_text, summary,
                     key_points, topic_tags, extraction_method, confidence,
                     model_config_id, created_at, page_metadata, latency_ms,
                     extraction_latency_ms, warnings, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    output_id,
                    result.file_id,
                    extraction.raw_text if extraction else "",
                    result.cleaned_text,
                    result.summary,
                    json.dumps(result.key_points),
                    json.dumps(result.topic_tags),
                    extraction.method.value if extraction else ExtractionMethod.UNKNOWN.value,
                    extraction.confidence if extraction else 0.0,
                    None,
                    now,
                    json.dumps(extraction.page_metadata if extraction else []),
                    result.latency_ms,
                    extraction.latency_ms if extraction else 0,
                    json.dumps(extraction.warnings if extraction else []),
                    result.error_message,
                ),
            )
        log.info("ProcessingResult saved", extra={"file_id": result.file_id, "output_id": output_id})
        return output_id

    def get_processing_result(self, file_id: str) -> Optional[dict]:
        """Retrieve the most recent processing output for a file."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM processed_outputs
                WHERE file_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (file_id,),
            ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["key_points"] = json.loads(d.get("key_points") or "[]")
        d["topic_tags"] = json.loads(d.get("topic_tags") or "[]")
        d["page_metadata"] = json.loads(d.get("page_metadata") or "[]")
        d["warnings"] = json.loads(d.get("warnings") or "[]")
        return d

    def list_processed_file_ids(self) -> list[str]:
        """Return file_ids that have at least one processed output, newest first."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT file_id, MAX(created_at) AS last_created
                FROM processed_outputs
                GROUP BY file_id
                ORDER BY last_created DESC
                """
            ).fetchall()
        return [str(r["file_id"]) for r in rows]

    def list_queryable_file_ids(self) -> list[str]:
        """
        Return file_ids that have non-empty cleaned text in their latest processed output.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT p.file_id
                FROM processed_outputs p
                JOIN (
                    SELECT file_id, MAX(created_at) AS latest_created
                    FROM processed_outputs
                    GROUP BY file_id
                ) latest
                ON latest.file_id = p.file_id AND latest.latest_created = p.created_at
                WHERE p.cleaned_text IS NOT NULL AND TRIM(p.cleaned_text) <> ''
                ORDER BY p.created_at DESC
                """
            ).fetchall()
        return [str(r["file_id"]) for r in rows]

    # ── Chunks ─────────────────────────────────────────────────────────────

    def save_chunks(self, chunks: list[TextChunk]) -> None:
        """Bulk-insert text chunks; existing chunks for the file are replaced."""
        if not chunks:
            return
        file_id = chunks[0].file_id
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))
            conn.executemany(
                """
                INSERT INTO chunks (chunk_id, file_id, chunk_index, text, confidence, metadata, vector_ref)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        c.chunk_id,
                        c.file_id,
                        c.chunk_index,
                        c.text,
                        c.confidence,
                        json.dumps(c.metadata),
                        c.vector_ref,
                    )
                    for c in chunks
                ],
            )
        log.info("Chunks saved", extra={"file_id": file_id, "count": len(chunks)})

    def get_chunks(self, file_id: str) -> list[TextChunk]:
        """Retrieve all chunks for a file, ordered by chunk_index."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chunks WHERE file_id = ? ORDER BY chunk_index ASC",
                (file_id,),
            ).fetchall()
        return [
            TextChunk(
                chunk_id=r["chunk_id"],
                file_id=r["file_id"],
                chunk_index=r["chunk_index"],
                text=r["text"],
                confidence=r["confidence"] or 1.0,
                metadata=json.loads(r["metadata"] or "{}"),
                vector_ref=r["vector_ref"] or "",
            )
            for r in rows
        ]

    # ── Model metrics ──────────────────────────────────────────────────────

    def save_metric(self, metric: ModelMetric) -> None:
        if not metric.metric_id:
            metric.metric_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO model_metrics
                    (metric_id, file_id, stage, model_name, provider,
                     latency_ms, estimated_cost, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metric.metric_id,
                    metric.file_id,
                    metric.stage,
                    metric.model_name,
                    metric.provider,
                    metric.latency_ms,
                    metric.estimated_cost,
                    metric.status,
                    metric.error_message,
                ),
            )

    def get_metrics(self, file_id: str) -> list[ModelMetric]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM model_metrics WHERE file_id = ? ORDER BY rowid ASC",
                (file_id,),
            ).fetchall()
        return [
            ModelMetric(
                metric_id=r["metric_id"],
                file_id=r["file_id"],
                stage=r["stage"],
                model_name=r["model_name"] or "",
                provider=r["provider"] or "",
                latency_ms=r["latency_ms"] or 0,
                estimated_cost=r["estimated_cost"] or 0.0,
                status=r["status"] or "success",
                error_message=r["error_message"] or "",
            )
            for r in rows
        ]
