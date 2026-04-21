from __future__ import annotations

import unittest

from tri_model_assistant.core.config import SummaryLength
from tri_model_assistant.processing.text_processing import build_refinement_prompt, chunk_text, split_paragraphs


class TextProcessingTests(unittest.TestCase):
    def test_split_paragraphs_removes_empty_blocks(self) -> None:
        text = "Paragraph one.\n\n\nParagraph two.\n\nParagraph three."
        self.assertEqual(split_paragraphs(text), ["Paragraph one.", "Paragraph two.", "Paragraph three."])

    def test_chunk_text_keeps_paragraph_boundaries(self) -> None:
        text = (
            "alpha beta gamma\n\n"
            "delta epsilon zeta eta\n\n"
            "theta iota kappa lambda mu\n\n"
            "nu xi omicron"
        )
        chunks = chunk_text(text=text, max_words_per_chunk=8, overlap_paragraphs=0)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].text, "alpha beta gamma\n\ndelta epsilon zeta eta")
        self.assertEqual(chunks[1].text, "theta iota kappa lambda mu\n\nnu xi omicron")

    def test_refinement_prompt_changes_with_length(self) -> None:
        draft_summary = "A short draft summary."

        short_prompt = build_refinement_prompt(draft_summary, SummaryLength.SHORT)
        medium_prompt = build_refinement_prompt(draft_summary, SummaryLength.MEDIUM)
        long_prompt = build_refinement_prompt(draft_summary, SummaryLength.LONG)

        self.assertIn("15 to 30 words", short_prompt)
        self.assertIn("35 to 60 words", medium_prompt)
        self.assertIn("70 to 110 words", long_prompt)
        self.assertIn("longer than the short version", medium_prompt)
        self.assertIn("most detailed version", long_prompt)
        self.assertIn(draft_summary, short_prompt)


if __name__ == "__main__":
    unittest.main()
