"""Canonical document model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DocumentSourceType(str, Enum):
    PDF = "pdf"
    URL = "url"
    BLOG = "blog"
    TEXT = "text"


@dataclass(slots=True)
class Document:
    """Normalized source document used throughout the pipelines."""

    document_id: str
    source_type: str
    source: str
    title: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def reference_label(self) -> str:
        return self.title or self.source
