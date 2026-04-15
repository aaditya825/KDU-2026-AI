from __future__ import annotations

import unittest

from src.core.config import load_settings
from src.core.models import Chunk, Query, Response, RetrievedChunk
from src.generation.llms import GeminiLLM, LLMFactory
from src.generation.prompts import PromptManager
from src.ingestion.loaders import LoaderFactory, PDFLoader
from src.retrieval.pipeline import RetrievalPipeline


class StubRetriever:
    def retrieve(self, query: Query) -> list[RetrievedChunk]:
        chunk = Chunk(
            chunk_id="chunk-1",
            document_id="doc-1",
            text="retrieved content",
            position=1,
            start_offset=0,
            end_offset=17,
            section_title="Intro",
            metadata={"document_title": "Doc 1", "source": "source-a"},
        )
        return [RetrievedChunk(chunk=chunk, retrieval_source="semantic", score=0.9)]


class StubUnavailableReranker:
    def is_available(self) -> bool:
        return False


class ScaffoldTests(unittest.TestCase):
    def test_loader_factory_returns_registered_loader(self) -> None:
        loader = LoaderFactory.create("pdf")
        self.assertIsInstance(loader, PDFLoader)

    def test_load_settings_uses_yaml_defaults(self) -> None:
        settings = load_settings(config_path="config/config.yaml", env_path=".env.example")
        self.assertEqual(settings.chunking.chunk_size, 512)
        self.assertEqual(settings.retrieval.semantic_top_k, 10)
        self.assertEqual(settings.storage.vector_store, "chromadb")
        self.assertEqual(settings.generation.provider, "gemini")
        self.assertEqual(settings.generation.model_name, "gemini-2.5-flash")

    def test_llm_factory_default_is_gemini(self) -> None:
        provider = LLMFactory.create_default()
        self.assertIsInstance(provider, GeminiLLM)

    def test_retrieval_pipeline_falls_back_when_reranker_unavailable(self) -> None:
        pipeline = RetrievalPipeline(retriever=StubRetriever(), reranker=StubUnavailableReranker())
        results = pipeline.retrieve(Query(query_text="test", top_k=1))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].chunk.chunk_id, "chunk-1")

    def test_insufficient_context_response_contract(self) -> None:
        response = Response.from_insufficient_context(metadata={"phase": "scaffold"})
        self.assertEqual(response.answer, "The answer is not available from the provided sources.")
        self.assertTrue(response.metadata["insufficient_context"])

    def test_prompt_manager_renders_expected_prompt(self) -> None:
        manager = PromptManager()
        prompt = manager.render_user_prompt(question="What is RAG?", context="Context block")
        self.assertIn("What is RAG?", prompt)
        self.assertIn("Context block", prompt)


if __name__ == "__main__":
    unittest.main()
