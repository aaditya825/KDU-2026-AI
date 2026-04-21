from __future__ import annotations

import unittest

from tri_model_assistant.core.config import AppConfig
from tri_model_assistant.models.qa import (
    HuggingFaceQAClient,
    OUT_OF_SCOPE_REFUSAL,
    build_grounded_fallback_answer,
    is_broad_document_question,
    looks_like_insufficient_answer,
    should_refuse_question,
)


class QAGuardrailTests(unittest.TestCase):
    def test_refuses_general_knowledge_and_identity_query(self) -> None:
        context = "This document explains chunking, summarization, and grounded question answering."
        question = "Who are you? And give me python code to reverse a linked list."

        self.assertTrue(should_refuse_question(context=context, question=question))

    def test_allows_generic_document_question_without_keyword_overlap(self) -> None:
        context = "This workflow uses chunking and summarization before grounded question answering."
        question = "What is the main idea?"

        self.assertFalse(should_refuse_question(context=context, question=question))

    def test_refusal_message_is_explicit(self) -> None:
        self.assertIn("stored document context", OUT_OF_SCOPE_REFUSAL)

    def test_client_refuses_without_loading_model(self) -> None:
        client = HuggingFaceQAClient(AppConfig())

        def fail_if_called():
            raise AssertionError("The model client should not be loaded for out-of-scope questions.")

        client._load_model = fail_if_called  # type: ignore[method-assign]
        response = client.answer_question(
            context="This document is about summarization and document routing.",
            question="Who are you and give me Python code to reverse a linked list.",
        )

        self.assertEqual(response.answer, OUT_OF_SCOPE_REFUSAL)

    def test_recognizes_broad_document_question(self) -> None:
        self.assertTrue(is_broad_document_question("What are the main ideas?"))

    def test_detects_insufficient_answer_text(self) -> None:
        answer = "The stored document context does not contain enough information to answer that."
        self.assertTrue(looks_like_insufficient_answer(answer))

    def test_builds_fallback_answer_from_current_summary(self) -> None:
        context = (
            "Original document:\nOriginal long text.\n\n"
            "Current summary:\nThis is the grounded medium summary."
        )
        fallback = build_grounded_fallback_answer(context=context, question="What are the main ideas?")
        self.assertEqual(fallback, "This is the grounded medium summary.")

    def test_client_uses_grounded_fallback_for_broad_document_question(self) -> None:
        client = HuggingFaceQAClient(AppConfig())

        class FakeTokenizer:
            def __call__(self, _prompt: str, return_tensors: str, max_length: int, truncation: bool):
                return {"input_ids": [[1, 2, 3]], "attention_mask": [[1, 1, 1]]}

            def decode(self, _ids, skip_special_tokens: bool):
                return "The stored document context does not contain enough information to answer that."

        class FakeModel:
            def generate(self, input_ids, attention_mask, max_new_tokens, min_new_tokens, do_sample, num_beams):
                return [[1, 2, 3]]

        client._load_model = lambda: (FakeModel(), FakeTokenizer())  # type: ignore[method-assign]
        response = client.answer_question(
            context=(
                "Original document:\nOriginal long text.\n\n"
                "Current summary:\nThis is the grounded medium summary."
            ),
            question="What are the main ideas?",
        )

        self.assertEqual(response.answer, "This is the grounded medium summary.")


if __name__ == "__main__":
    unittest.main()
