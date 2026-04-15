"""Plain-text loader used for internal normalization and tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

from src.core.interfaces import DocumentLoader
from src.core.models import Document


class TextLoader(DocumentLoader):
    supported_source_types = ("text",)

    def __init__(self, *, source_label: str = "inline-text") -> None:
        self.source_label = source_label

    def load(self, source: str) -> Document:
        source_path = Path(source)
        if source_path.exists():
            text = source_path.read_text(encoding="utf-8")
            origin = str(source_path.resolve())
            title = source_path.stem
        else:
            text = source
            origin = self.source_label
            title = self.source_label

        normalized = text.strip()
        if not normalized:
            raise ValueError("Text source contained no readable content.")

        document_id = hashlib.sha256(f"text::{origin}".encode("utf-8")).hexdigest()
        return Document(
            document_id=document_id,
            source_type="text",
            source=origin,
            title=title,
            content=normalized,
            metadata={
                "document_title": title,
                "source": origin,
                "source_type": "text",
                "sections": [
                    {
                        "title": title,
                        "text": normalized,
                        "start_offset": 0,
                        "end_offset": len(normalized),
                        "metadata": {},
                    }
                ],
            },
        )
