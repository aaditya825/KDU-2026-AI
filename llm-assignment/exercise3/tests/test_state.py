from __future__ import annotations

import unittest

from tri_model_assistant.core.state import AssistantState


class AssistantStateContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = AssistantState(
            original_text=(
                "Routing decides which model handles each user query.\n\n"
                "Chunking helps process large documents that exceed model limits.\n\n"
                "State persistence stores draft and refined summaries for later reuse.\n\n"
                "Grounded QA should answer only from retrieved context chunks."
            )
        )

    def test_select_relevant_chunks_prefers_overlap_with_query(self) -> None:
        selected = self.state.select_relevant_original_chunks(
            query="Why does chunking help with model context limits?",
            max_words_per_chunk=7,
            overlap_paragraphs=0,
            max_chunks=2,
        )

        selected_text = " ".join(chunk.text.lower() for chunk in selected)
        self.assertIn("chunking", selected_text)
        self.assertLessEqual(len(selected), 2)

    def test_build_qa_context_reports_retrieved_chunks_source(self) -> None:
        source, context = self.state.build_qa_context(
            query="How does retrieval chunking work?",
            qa_chunk_word_limit=7,
            qa_chunk_overlap_paragraphs=0,
            qa_max_chunks=2,
        )

        self.assertIn("retrieved_chunks", source)
        self.assertIn("[Chunk", context)


if __name__ == "__main__":
    unittest.main()
