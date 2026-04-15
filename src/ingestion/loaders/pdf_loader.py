"""PDF loader implementation."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pypdf import PdfReader

from src.core.interfaces import DocumentLoader
from src.core.models import Document
from src.utils.logger import get_logger


logger = get_logger(__name__)


class PDFLoader(DocumentLoader):
    supported_source_types = ("pdf",)

    def load(self, source: str) -> Document:
        source_path = Path(source).expanduser()
        if not source_path.exists():
            raise FileNotFoundError(f"PDF source not found: {source_path}")
        if source_path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a PDF file, received: {source_path}")

        try:
            reader = PdfReader(str(source_path))
        except Exception as exc:
            logger.exception("event=loader.pdf.read_failed source=%s", source_path)
            raise ValueError(
                f"Failed to read PDF '{source_path.name}'. Ensure the file is a valid PDF with extractable text."
            ) from exc
        pages: list[dict[str, object]] = []
        page_texts: list[str] = []
        sections: list[dict[str, object]] = []
        current_offset = 0

        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            pages.append({"page_number": page_number, "char_count": len(text)})
            page_texts.append(text)
            sections.append(
                {
                    "title": f"Page {page_number}",
                    "text": text,
                    "start_offset": current_offset,
                    "end_offset": current_offset + len(text),
                    "metadata": {"page_number": page_number},
                }
            )
            current_offset += len(text) + 2

        if not page_texts:
            raise ValueError(f"PDF contained no extractable text: {source_path}")

        metadata = reader.metadata or {}
        title = getattr(metadata, "title", None)
        if not title and hasattr(metadata, "get"):
            title = metadata.get("/Title")
        resolved_source = str(source_path.resolve())
        document_id = hashlib.sha256(f"pdf::{resolved_source}".encode("utf-8")).hexdigest()

        return Document(
            document_id=document_id,
            source_type="pdf",
            source=resolved_source,
            title=(title or source_path.stem).strip(),
            content="\n\n".join(page_texts),
            metadata={
                "document_title": (title or source_path.stem).strip(),
                "source": resolved_source,
                "source_type": "pdf",
                "pages": pages,
                "sections": sections,
                "page_count": len(reader.pages),
            },
        )
