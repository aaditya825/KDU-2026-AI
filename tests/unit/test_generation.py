from __future__ import annotations

import unittest

from src.core.models import Chunk, Query, RetrievedChunk
from src.generation.context_builder import ContextBuilder
from src.generation.generator import ResponseGenerator
from src.generation.llms.gemini_llm import GeminiLLM
from src.generation.prompts import PromptManager


def make_retrieved_chunk(chunk_id: str, text: str, position: int = 1) -> RetrievedChunk:
    chunk = Chunk(
        chunk_id=chunk_id,
        document_id="doc-1",
        text=text,
        position=position,
        start_offset=0,
        end_offset=len(text),
        section_title="Overview",
        metadata={"document_title": "Fixture Doc", "source": "fixture.txt", "source_type": "text"},
    )
    return RetrievedChunk(
        chunk=chunk,
        retrieval_source="keyword+semantic",
        score=0.9,
        rank=position,
        document_title="Fixture Doc",
        document_source="fixture.txt",
    )


class StubLLM:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls = 0

    def generate(self, prompt, *, system_prompt=None, metadata=None):
        self.calls += 1
        return self.answer


class FailingLLM:
    def generate(self, prompt, *, system_prompt=None, metadata=None):
        raise RuntimeError("boom")


class StubGeminiResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class StubGeminiModels:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return StubGeminiResponse("Grounded Gemini answer [1].")


class StubGeminiClient:
    def __init__(self) -> None:
        self.models = StubGeminiModels()


class GenerationTests(unittest.TestCase):
    def test_context_builder_produces_context_and_citations(self) -> None:
        builder = ContextBuilder(prompt_manager=PromptManager())
        context, citations = builder.build([make_retrieved_chunk("chunk-1", "Hybrid retrieval text", 2)])

        self.assertIn("Fixture Doc", context)
        self.assertIn("chunk 2", context)
        self.assertEqual(citations[0].chunk_position, 2)
        self.assertEqual(citations[0].snippet, "Hybrid retrieval text")

    def test_response_generator_appends_citations_to_answer(self) -> None:
        generator = ResponseGenerator(llm_provider=StubLLM("Hybrid retrieval combines search modes [1]."))
        response = generator.generate(
            Query(query_text="What is hybrid retrieval?", top_k=5),
            [make_retrieved_chunk("chunk-1", "Hybrid retrieval text", 1)],
        )

        self.assertIn("Citations:", response.answer)
        self.assertEqual(len(response.sources), 1)

    def test_response_generator_handles_insufficient_context(self) -> None:
        generator = ResponseGenerator(llm_provider=StubLLM("unused"))
        response = generator.generate(Query(query_text="Unknown question", top_k=5), [])
        self.assertTrue(response.metadata["user_error"].startswith("No relevant context"))

    def test_response_generator_handles_llm_failures(self) -> None:
        generator = ResponseGenerator(llm_provider=FailingLLM())
        response = generator.generate(
            Query(query_text="Question", top_k=5),
            [make_retrieved_chunk("chunk-1", "Hybrid retrieval text", 1)],
        )
        self.assertIn("language model request failed", response.answer.lower())
        self.assertIn("user_error", response.metadata)

    def test_gemini_llm_uses_client_generate_content(self) -> None:
        client = StubGeminiClient()
        llm = GeminiLLM(client=client, api_key="test-key")

        answer = llm.generate(
            "What is hybrid retrieval?",
            system_prompt="Use only the provided context.",
        )

        self.assertEqual(answer, "Grounded Gemini answer [1].")
        self.assertEqual(client.models.calls[0]["model"], "gemini-2.5-flash")
        self.assertEqual(client.models.calls[0]["contents"], "What is hybrid retrieval?")


if __name__ == "__main__":
    unittest.main()
