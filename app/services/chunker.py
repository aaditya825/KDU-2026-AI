"""
app/services/chunker.py
────────────────────────
Split cleaned text into overlapping chunks for vector indexing.

Strategy:
  - Split on paragraph boundaries first; fall back to sentence boundaries.
  - Paragraphs longer than chunk_size are split at character boundaries.
  - Target chunk size comes from model_registry and is kept below the
    embedding model's practical input window.
  - Overlap comes from model_registry to preserve context across chunks.
  - Each chunk carries source metadata (file_id, chunk_index, confidence).
"""

from __future__ import annotations

import uuid
from typing import Any
import re

from app.config.model_registry import (
    DEFAULT_EMBEDDING_CHUNK_OVERLAP_CHARS,
    DEFAULT_EMBEDDING_CHUNK_SIZE_CHARS,
)
from app.models.domain import TextChunk

_CHUNK_SIZE = DEFAULT_EMBEDDING_CHUNK_SIZE_CHARS
_OVERLAP = DEFAULT_EMBEDDING_CHUNK_OVERLAP_CHARS
_MIN_CHUNK_CHARS = 50   # discard chunks shorter than this


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs, then further split overlong paragraphs."""
    raw_blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    if len(raw_blocks) <= 1:
        raw_blocks = [b.strip() for b in text.split("\n") if b.strip()]

    blocks: list[str] = []
    for block in raw_blocks:
        if len(block) <= _CHUNK_SIZE:
            blocks.append(block)
        else:
            # Split overlong paragraph at sentence boundaries or character boundaries
            sub = _split_long_block(block, _CHUNK_SIZE)
            blocks.extend(sub)
    return blocks


def _split_long_block(text: str, size: int) -> list[str]:
    """Split a block that is longer than *size* into pieces at sentence ends."""
    # Try sentence boundaries first
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    parts: list[str] = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) > size and current:
            parts.append(current.strip())
            current = sent
        else:
            current = (current + " " + sent).strip() if current else sent
    if current:
        parts.append(current.strip())

    # If any part is still too long, hard-cut at character boundaries
    result: list[str] = []
    for part in parts:
        if len(part) <= size:
            result.append(part)
        else:
            for i in range(0, len(part), size):
                result.append(part[i:i + size])
    return [p for p in result if p]


def chunk_text(
    text: str,
    file_id: str,
    file_name: str = "",
    confidence: float = 1.0,
    extra_metadata: dict[str, Any] | None = None,
    chunk_size: int = _CHUNK_SIZE,
    overlap: int = _OVERLAP,
) -> list[TextChunk]:
    """
    Split *text* into overlapping TextChunk objects.

    Parameters
    ----------
    text:
        The cleaned document text to split.
    file_id:
        The file_id to embed in each chunk's metadata.
    file_name:
        The original filename, stored in metadata for display.
    confidence:
        Extraction confidence score carried forward to each chunk.
    extra_metadata:
        Additional key-value pairs to attach to every chunk.
    chunk_size:
        Target character count per chunk.
    overlap:
        Overlap character count between consecutive chunks.

    Returns
    -------
    list[TextChunk]
        Ordered, non-empty chunks ready for embedding.
    """
    if not text.strip():
        return []

    paragraphs = _split_paragraphs(text)
    chunks: list[TextChunk] = []
    current: list[str] = []
    current_len = 0
    chunk_index = 0

    def _flush(parts: list[str], idx: int) -> TextChunk:
        body = "\n\n".join(parts).strip()
        page_matches = sorted({int(p) for p in re.findall(r"\[PAGE\s+(\d+)\]", body)})
        metadata: dict[str, Any] = {
            "file_id": file_id,
            "file_name": file_name,
            "chunk_index": idx,
            "pages": page_matches,
        }
        if extra_metadata:
            metadata.update(extra_metadata)
        return TextChunk(
            chunk_id=str(uuid.uuid4()),
            file_id=file_id,
            chunk_index=idx,
            text=body,
            confidence=confidence,
            metadata=metadata,
        )

    for para in paragraphs:
        if current_len + len(para) > chunk_size and current:
            chunk = _flush(current, chunk_index)
            if len(chunk.text) >= _MIN_CHUNK_CHARS:
                chunks.append(chunk)
                chunk_index += 1

            # Keep overlap: walk back from the end until we have ~overlap chars
            overlap_parts: list[str] = []
            overlap_len = 0
            for part in reversed(current):
                if overlap_len + len(part) > overlap:
                    break
                overlap_parts.insert(0, part)
                overlap_len += len(part)
            current = overlap_parts
            current_len = overlap_len

        current.append(para)
        current_len += len(para)

    # Flush remaining
    if current:
        chunk = _flush(current, chunk_index)
        if len(chunk.text) >= _MIN_CHUNK_CHARS:
            chunks.append(chunk)

    return chunks
