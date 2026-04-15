"""Lightweight validation helpers for core contracts."""

from __future__ import annotations

from src.core.models import Chunk, Document, Query


class ValidationError(ValueError):
    """Raised when a core contract is malformed."""


def _require_text(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")


def validate_document(document: Document) -> None:
    _require_text(document.document_id, "document_id")
    _require_text(document.source_type, "source_type")
    _require_text(document.source, "source")
    _require_text(document.title, "title")
    _require_text(document.content, "content")


def validate_chunk(chunk: Chunk) -> None:
    _require_text(chunk.chunk_id, "chunk_id")
    _require_text(chunk.document_id, "document_id")
    _require_text(chunk.text, "text")
    if chunk.position < 0:
        raise ValidationError("position must be non-negative.")
    if chunk.end_offset < chunk.start_offset:
        raise ValidationError("end_offset must be greater than or equal to start_offset.")


def validate_query(query: Query) -> None:
    _require_text(query.query_text, "query_text")
    if query.top_k <= 0:
        raise ValidationError("top_k must be greater than zero.")
