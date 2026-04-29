"""
app/models/domain.py
────────────────────
Core domain dataclasses shared across all phases.

Phase 1: FileMetadata, FileStatus, FileType
Phase 2: ExtractionResult, ProcessingResult, TextChunk
Phase 3: SearchResult, AnswerResult, ModelMetric, ComparisonReport
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ─────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────

class FileStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileType(str, Enum):
    PDF = "pdf"
    IMAGE = "image"
    AUDIO = "audio"


class ExtractionMethod(str, Enum):
    DIRECT_TEXT = "direct_text"
    OCR = "ocr"
    VISION = "vision"
    WHISPER = "whisper"
    FASTER_WHISPER = "faster_whisper"
    UNKNOWN = "unknown"


# ─────────────────────────────────────────────
# Phase 1 — File ingestion
# ─────────────────────────────────────────────

@dataclass
class FileMetadata:
    """Tracks a single uploaded file from ingestion through processing."""
    file_id: str
    original_name: str
    stored_path: str
    file_type: FileType
    mime_type: str
    size_bytes: int
    status: FileStatus = FileStatus.UPLOADED
    created_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "original_name": self.original_name,
            "stored_path": self.stored_path,
            "file_type": self.file_type.value,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# ─────────────────────────────────────────────
# Phase 2
# ─────────────────────────────────────────────

@dataclass
class ExtractionResult:
    """Raw extraction output from a pipeline (PDF, image, or audio)."""
    raw_text: str = ""
    confidence: float = 1.0          # 0.0–1.0; <0.5 is low-confidence
    method: ExtractionMethod = ExtractionMethod.UNKNOWN
    page_metadata: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    latency_ms: int = 0


@dataclass
class ProcessingResult:
    """Final structured output after post-processing."""
    file_id: str = ""
    cleaned_text: str = ""
    summary: str = ""
    key_points: list[str] = field(default_factory=list)
    topic_tags: list[str] = field(default_factory=list)
    extraction: Optional[ExtractionResult] = None
    latency_ms: int = 0
    error_message: str = ""


# ─────────────────────────────────────────────
# Phase 3
# ─────────────────────────────────────────────

@dataclass
class TextChunk:
    """A single chunk ready for embedding and vector-store indexing."""
    chunk_id: str = ""
    file_id: str = ""
    chunk_index: int = 0
    text: str = ""
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    vector_ref: str = ""


@dataclass
class SearchResult:
    """A single vector search hit with supporting metadata."""
    chunk_text: str = ""
    score: float = 0.0
    file_id: str = ""
    file_name: str = ""
    chunk_index: int = 0
    confidence: float = 1.0
    source_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnswerResult:
    """Grounded Q&A response with supporting chunks."""
    answer: str = ""
    supporting_chunks: list[SearchResult] = field(default_factory=list)
    confidence_notes: str = ""
    insufficient_evidence: bool = False


@dataclass
class ModelMetric:
    """Latency and cost record for a single processing stage."""
    metric_id: str = ""
    file_id: str = ""
    stage: str = ""
    model_name: str = ""
    provider: str = ""
    latency_ms: int = 0
    estimated_cost: float = 0.0
    status: str = "success"
    error_message: str = ""


@dataclass
class ComparisonReport:
    """Aggregated result from running multiple model configs on one file."""
    file_id: str = ""
    model_results: list[dict[str, Any]] = field(default_factory=list)
    metric_summary: dict[str, Any] = field(default_factory=dict)
    observations: str = ""
