"""Query contract for retrieval and generation flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Query:
    """Represents a user question and retrieval parameters."""

    query_text: str
    top_k: int
    filters: dict[str, Any] = field(default_factory=dict)
    session_id: str = "default"
    metadata: dict[str, Any] = field(default_factory=dict)
