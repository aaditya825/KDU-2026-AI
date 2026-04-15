"""Contextual chunker implementation with section-aware splitting."""

from __future__ import annotations

import hashlib

from src.core.interfaces import Chunker
from src.core.models import Chunk, Document
from src.ingestion.chunkers.recursive_chunker import RecursiveChunker


class ContextualChunker(Chunker):
    def __init__(self, *, chunk_size: int = 512, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.fallback_chunker = RecursiveChunker(chunk_size=chunk_size, overlap=overlap)

    def chunk(self, document: Document) -> list[Chunk]:
        sections = self._extract_sections(document)
        chunks: list[Chunk] = []
        position = 1

        for index, section in enumerate(sections):
            section_text = str(section.get("text", "")).strip()
            if not section_text:
                continue
            section_title = str(section.get("title", "") or document.title)
            section_start = int(section.get("start_offset", 0))
            section_metadata = dict(section.get("metadata", {}))
            previous_title = str(sections[index - 1].get("title", "")) if index > 0 else ""
            next_title = str(sections[index + 1].get("title", "")) if index + 1 < len(sections) else ""

            for window in self.fallback_chunker.split_text(section_text, base_offset=section_start):
                chunk_id = hashlib.sha256(
                    f"{document.document_id}:{position}:{window.start_offset}:{window.end_offset}".encode("utf-8")
                ).hexdigest()
                metadata = {
                    "source": document.source,
                    "source_type": document.source_type,
                    "document_title": document.title,
                    "section_index": index,
                    "previous_section_title": previous_title,
                    "next_section_title": next_title,
                }
                metadata.update(document.metadata)
                metadata.update(section_metadata)
                metadata["sections"] = None
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        document_id=document.document_id,
                        text=window.text,
                        position=position,
                        start_offset=window.start_offset,
                        end_offset=window.end_offset,
                        section_title=section_title,
                        metadata=metadata,
                    )
                )
                position += 1

        if not chunks:
            raise ValueError(f"No chunks were produced for document {document.document_id}.")
        return chunks

    def _extract_sections(self, document: Document) -> list[dict[str, object]]:
        sections = document.metadata.get("sections")
        if isinstance(sections, list) and sections:
            return [section for section in sections if isinstance(section, dict)]
        return [
            {
                "title": document.title,
                "text": document.content,
                "start_offset": 0,
                "end_offset": len(document.content),
                "metadata": {},
            }
        ]
