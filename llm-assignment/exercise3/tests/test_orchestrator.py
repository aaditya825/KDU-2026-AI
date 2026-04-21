from __future__ import annotations

import unittest

from tri_model_assistant.core.config import SummaryLength
from tri_model_assistant.core.orchestrator import QueryRoutedAssistant
from tri_model_assistant.models.pipeline import SummaryArtifacts
from tri_model_assistant.core.router import QueryRouter, Route
from tri_model_assistant.core.state import AssistantState
from tri_model_assistant.processing.text_processing import Chunk, word_count


class FakeModelGateway:
    def __init__(self) -> None:
        self.generate_calls = 0
        self.refine_calls: list[SummaryLength] = []
        self.summarizer_model_name = "fake-summarizer"
        self.refiner_model_name = "fake-refiner"
        self.qa_chunk_word_limit = 8
        self.qa_chunk_overlap_paragraphs = 0
        self.qa_max_chunks = 2

    def generate_draft_summary(self, source_text: str) -> SummaryArtifacts:
        self.generate_calls += 1
        draft_summary = " ".join(f"draft{i}" for i in range(1, 121))
        return SummaryArtifacts(
            chunks=[Chunk(index=0, text=source_text, word_count=len(source_text.split()))],
            chunk_summaries=["draft chunk summary"],
            draft_summary=draft_summary,
        )

    def refine_summary(self, draft_summary: str, summary_length: SummaryLength) -> str:
        self.refine_calls.append(summary_length)
        if summary_length is SummaryLength.SHORT:
            return " ".join(["short"] * 20)
        if summary_length is SummaryLength.MEDIUM:
            return " ".join(["medium"] * 45)
        return " ".join(["long"] * 85)


class FakeQAClient:
    def __init__(self) -> None:
        self.last_context: str | None = None
        self.last_question: str | None = None
        self.calls = 0
        self.model_name = "fake-qa-model"

    class _Response:
        def __init__(self, answer: str) -> None:
            self.answer = answer

    def answer_question(self, context: str, question: str):
        self.calls += 1
        self.last_context = context
        self.last_question = question
        return self._Response(answer=f"answer from {context}")


class RepetitiveRefinementGateway:
    def __init__(self) -> None:
        self.summarizer_model_name = "fake-summarizer"
        self.refiner_model_name = "fake-refiner"
        self.qa_chunk_word_limit = 8
        self.qa_chunk_overlap_paragraphs = 0
        self.qa_max_chunks = 2

    def generate_draft_summary(self, source_text: str) -> SummaryArtifacts:
        draft_summary = " ".join(f"draft{i}" for i in range(1, 121))
        return SummaryArtifacts(
            chunks=[Chunk(index=0, text=source_text, word_count=len(source_text.split()))],
            chunk_summaries=["draft chunk summary"],
            draft_summary=draft_summary,
        )

    def refine_summary(self, draft_summary: str, summary_length: SummaryLength) -> str:
        return "repeated refinement text repeated refinement text repeated refinement text"


class QueryRoutedAssistantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model_gateway = FakeModelGateway()
        self.qa_client = FakeQAClient()
        self.assistant = QueryRoutedAssistant(
            assistant_state=AssistantState(original_text="source document text"),
            router=QueryRouter(),
            model_gateway=self.model_gateway,
            qa_client=self.qa_client,
        )

    def test_summarize_route_generates_draft_once(self) -> None:
        first = self.assistant.handle_query("Summarize this document")
        second = self.assistant.handle_query("Give me the summary")

        self.assertEqual(first.route, Route.SUMMARIZE)
        self.assertIn("Summarization", first.model_used or "")
        self.assertEqual(second.route, Route.SUMMARIZE)
        self.assertEqual(self.model_gateway.generate_calls, 1)
        self.assertEqual(word_count(self.assistant.state.draft_summary or ""), 120)

    def test_refine_route_generates_and_caches_requested_length(self) -> None:
        first = self.assistant.handle_query("Give me a short summary")
        second = self.assistant.handle_query("Make it shorter")

        self.assertEqual(first.route, Route.REFINE_SHORT)
        self.assertIn("Refinement", first.model_used or "")
        self.assertEqual(second.route, Route.REFINE_SHORT)
        self.assertEqual(self.model_gateway.generate_calls, 1)
        self.assertEqual(self.model_gateway.refine_calls, [SummaryLength.SHORT])
        self.assertEqual(word_count(self.assistant.state.short_summary or ""), 20)

    def test_qa_route_uses_current_summary_when_available(self) -> None:
        self.assistant.handle_query("Give me a medium summary")
        outcome = self.assistant.handle_query("What are the key risks?")

        self.assertEqual(outcome.route, Route.QA)
        self.assertIn("QA", outcome.model_used or "")
        self.assertIn("Original document:\n[Chunk 0]\nsource document text", self.qa_client.last_context or "")
        self.assertIn("Current summary:\nmedium medium medium", self.qa_client.last_context or "")
        self.assertEqual(outcome.context_source, "retrieved_chunks+current_summary")
        self.assertEqual(self.qa_client.calls, 1)

    def test_refinement_ordering_is_enforced_against_existing_summaries(self) -> None:
        assistant = QueryRoutedAssistant(
            assistant_state=AssistantState(
                original_text="source document text",
                draft_summary=" ".join(f"draft{i}" for i in range(1, 121)),
                short_summary=" ".join(["short"] * 25),
            ),
            router=QueryRouter(),
            model_gateway=self.model_gateway,
            qa_client=self.qa_client,
        )

        self.model_gateway.refine_summary = lambda draft_summary, summary_length: "tiny output"  # type: ignore[method-assign]
        outcome = assistant.handle_query("Give me a medium summary")

        self.assertEqual(outcome.route, Route.REFINE_MEDIUM)
        self.assertGreater(word_count(assistant.state.medium_summary or ""), word_count(assistant.state.short_summary or ""))

    def test_repetitive_refinement_outputs_are_forced_into_distinct_bands(self) -> None:
        assistant = QueryRoutedAssistant(
            assistant_state=AssistantState(
                original_text=(
                    "The assistant stores one document and answers follow-up questions from it. "
                    "A router decides whether the user wants a summary, a shorter rewrite, a longer rewrite, or QA. "
                    "The summarizer creates a draft from the source document. "
                    "The refiner reshapes that draft into distinct length bands. "
                    "The QA model uses the stored context to answer grounded questions. "
                    "Weak sample text can hide those differences, so the input needs multiple themes."
                )
            ),
            router=QueryRouter(),
            model_gateway=RepetitiveRefinementGateway(),
            qa_client=self.qa_client,
        )

        short_outcome = assistant.handle_query("Give me a short summary")
        medium_outcome = assistant.handle_query("Give me a medium summary")
        long_outcome = assistant.handle_query("Make it more detailed")

        self.assertNotEqual(short_outcome.response, medium_outcome.response)
        self.assertNotEqual(medium_outcome.response, long_outcome.response)
        self.assertLess(word_count(short_outcome.response), word_count(medium_outcome.response))
        self.assertLess(word_count(medium_outcome.response), word_count(long_outcome.response))

    def test_exit_route_returns_exit_message(self) -> None:
        outcome = self.assistant.handle_query("exit")

        self.assertEqual(outcome.route, Route.EXIT)
        self.assertEqual(outcome.model_used, "None")
        self.assertIn("Exiting assistant", outcome.response)

    def test_qa_route_uses_retrieved_chunks_for_large_context(self) -> None:
        large_text = (
            "Routing selects the model based on the user request. "
            "The state object caches draft, short, medium, and long summaries.\n\n"
            "A chunking strategy is required when documents are too large for model context windows. "
            "Chunk-level retrieval should select only relevant sections for QA.\n\n"
            "Grounded QA must refuse unrelated questions and avoid outside knowledge. "
            "Fallback behavior should still remain faithful to stored context."
        )
        assistant = QueryRoutedAssistant(
            assistant_state=AssistantState(
                original_text=large_text,
                current_summary="A routed assistant with chunked retrieval for QA.",
            ),
            router=QueryRouter(),
            model_gateway=self.model_gateway,
            qa_client=self.qa_client,
        )

        outcome = assistant.handle_query("Why is chunking needed for large context windows?")

        self.assertEqual(outcome.route, Route.QA)
        self.assertIn("retrieved_chunks", outcome.context_source or "")
        self.assertIn("[Chunk", self.qa_client.last_context or "")
        self.assertIn("Current summary", self.qa_client.last_context or "")


if __name__ == "__main__":
    unittest.main()
