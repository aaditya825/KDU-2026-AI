"""Chunk model with traceability metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Chunk:
    """Represents a traceable text slice from a document."""

    chunk_id: str
    document_id: str
    text: str
    position: int
    start_offset: int
    end_offset: int
    section_title: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def short_reference(self) -> str:
        return f"{self.document_id}#{self.position}"
