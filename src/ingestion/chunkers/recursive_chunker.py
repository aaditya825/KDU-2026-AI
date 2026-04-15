"""Recursive chunker used as the fallback splitting strategy."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from src.core.interfaces import Chunker
from src.core.models import Chunk, Document


@dataclass(slots=True)
class TextWindow:
    text: str
    start_offset: int
    end_offset: int


class RecursiveChunker(Chunker):
    def __init__(self, *, chunk_size: int = 512, overlap: int = 50) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero.")
        if overlap < 0:
            raise ValueError("overlap must be non-negative.")
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size.")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document: Document) -> list[Chunk]:
        windows = self.split_text(document.content, base_offset=0)
        chunks: list[Chunk] = []
        for position, window in enumerate(windows, start=1):
            chunk_id = hashlib.sha256(
                f"{document.document_id}:{position}:{window.start_offset}:{window.end_offset}".encode("utf-8")
            ).hexdigest()
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=document.document_id,
                    text=window.text,
                    position=position,
                    start_offset=window.start_offset,
                    end_offset=window.end_offset,
                    section_title=document.title,
                    metadata={
                        "source": document.source,
                        "source_type": document.source_type,
                        "document_title": document.title,
                    },
                )
            )
        return chunks

    def split_text(self, text: str, *, base_offset: int = 0) -> list[TextWindow]:
        normalized = text.strip()
        if not normalized:
            return []

        windows: list[TextWindow] = []
        position = 0
        text_length = len(text)
        separators = ["\n\n", "\n", ". ", " "]
        minimum_window_chars = min(self.chunk_size, max(120, self.chunk_size // 2))

        while position < text_length:
            max_end = min(position + self.chunk_size, text_length)
            end = max_end
            if max_end < text_length:
                for separator in separators:
                    candidate = text.rfind(separator, position, max_end)
                    if candidate > position and (candidate - position) >= minimum_window_chars:
                        end = candidate + (1 if separator == ". " else 0)
                        break

            raw_chunk = text[position:end]
            stripped = raw_chunk.strip()
            if stripped:
                leading = len(raw_chunk) - len(raw_chunk.lstrip())
                trailing = len(raw_chunk) - len(raw_chunk.rstrip())
                start_offset = base_offset + position + leading
                end_offset = base_offset + end - trailing
                windows.append(TextWindow(text=stripped, start_offset=start_offset, end_offset=end_offset))

            if end >= text_length:
                break

            next_position = max(end - self.overlap, position + 1)
            while next_position < text_length and text[next_position].isspace():
                next_position += 1
            position = next_position

        return windows
