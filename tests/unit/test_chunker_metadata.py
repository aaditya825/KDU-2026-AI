from __future__ import annotations

from app.services.chunker import chunk_text


def test_chunker_extracts_page_metadata():
    text = (
        "[PAGE 1]\nAlpha section with enough text to exceed chunk minimum size.\n\n"
        "[PAGE 2]\nBeta section with additional content to keep the chunk valid."
    )
    chunks = chunk_text(text=text, file_id="f1", file_name="doc.pdf", confidence=0.8)
    assert chunks
    pages = chunks[0].metadata.get("pages")
    assert pages == [1, 2] or pages == [1]
