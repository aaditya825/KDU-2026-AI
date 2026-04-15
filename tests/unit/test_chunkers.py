from __future__ import annotations

import unittest

from src.core.models import Document
from src.ingestion.chunkers.contextual_chunker import ContextualChunker
from src.ingestion.chunkers.recursive_chunker import RecursiveChunker


class ChunkerTests(unittest.TestCase):
    def test_recursive_chunker_respects_overlap(self) -> None:
        text = "A" * 520 + " " + "B" * 520
        chunker = RecursiveChunker(chunk_size=512, overlap=50)
        windows = chunker.split_text(text)

        self.assertGreaterEqual(len(windows), 2)
        self.assertLessEqual(len(windows[0].text), 512)
        self.assertEqual(windows[1].start_offset, windows[0].end_offset - 50)

    def test_contextual_chunker_preserves_traceability_metadata(self) -> None:
        document = Document(
            document_id="doc-1",
            source_type="url",
            source="https://example.com/post",
            title="Example Post",
            content="Introduction paragraph.\n\nDetails paragraph.",
            metadata={
                "document_title": "Example Post",
                "source": "https://example.com/post",
                "source_type": "url",
                "sections": [
                    {
                        "title": "Intro",
                        "text": "Introduction paragraph.",
                        "start_offset": 0,
                        "end_offset": 23,
                        "metadata": {"heading_level": 1},
                    },
                    {
                        "title": "Details",
                        "text": "Details paragraph.",
                        "start_offset": 25,
                        "end_offset": 43,
                        "metadata": {"heading_level": 2},
                    },
                ],
            },
        )

        chunks = ContextualChunker(chunk_size=30, overlap=5).chunk(document)

        self.assertEqual(chunks[0].document_id, "doc-1")
        self.assertEqual(chunks[0].position, 1)
        self.assertEqual(chunks[0].section_title, "Intro")
        self.assertEqual(chunks[0].metadata["source"], "https://example.com/post")
        self.assertIn("heading_level", chunks[0].metadata)
        self.assertGreater(chunks[1].start_offset, chunks[0].start_offset)

    def test_recursive_chunker_does_not_fragment_into_tiny_windows_after_overlap(self) -> None:
        text = " ".join(f"Sentence {index}." for index in range(1, 120))
        windows = RecursiveChunker(chunk_size=128, overlap=20).split_text(text)

        self.assertLess(len(windows), 25)
        self.assertTrue(all(len(window.text) >= 60 for window in windows[:-1]))


if __name__ == "__main__":
    unittest.main()
