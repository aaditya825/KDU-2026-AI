"""Response contracts for generated answers and citations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.core.models.chunk import Chunk


@dataclass(slots=True)
class SourceCitation:
    """Renderable citation information for a generated answer."""

    document_id: str
    chunk_id: str
    source: str
    document_title: str
    chunk_position: int
    snippet: str = ""

    def label(self) -> str:
        return f"{self.document_title or self.source} (chunk {self.chunk_position})"


@dataclass(slots=True)
class RetrievedChunk:
    """Chunk plus retrieval provenance used for debugging and ranking."""

    chunk: Chunk
    retrieval_source: str
    score: float | None = None
    raw_scores: dict[str, float] = field(default_factory=dict)
    rank: int | None = None
    document_title: str | None = None
    document_source: str | None = None


@dataclass(slots=True)
class Response:
    """Final response returned by the generator layer."""

    answer: str
    sources: list[SourceCitation]
    retrieved_chunks: list[RetrievedChunk]
    latency_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_insufficient_context(
        cls,
        *,
        retrieved_chunks: list[RetrievedChunk] | None = None,
        latency_ms: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> "Response":
        payload = dict(metadata or {})
        payload["insufficient_context"] = True
        return cls(
            answer="The answer is not available from the provided sources.",
            sources=[],
            retrieved_chunks=retrieved_chunks or [],
            latency_ms=latency_ms,
            metadata=payload,
        )
