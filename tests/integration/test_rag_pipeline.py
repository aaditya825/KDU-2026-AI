from __future__ import annotations

import gc
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.config import load_settings
from src.orchestration.cache_manager import CacheManager
from src.orchestration.rag_pipeline import RAGPipeline
from src.orchestration.session_manager import SessionManager
from src.retrieval.rerankers.cross_encoder_reranker import CrossEncoderReranker


class StubEmbedder:
    def __init__(self) -> None:
        self.query_calls = 0

    def embed_texts(self, texts):
        vectors = []
        for text in texts:
            lowered = text.lower()
            vectors.append(
                [
                    1.0 if "hybrid retrieval" in lowered else 0.0,
                    1.0 if "keyword" in lowered else 0.0,
                ]
            )
        return vectors

    def embed_query(self, query_text):
        self.query_calls += 1
        lowered = query_text.lower()
        return [
            1.0 if "hybrid retrieval" in lowered else 0.0,
            1.0 if "keyword" in lowered else 0.0,
        ]


class WikiStubEmbedder:
    def __init__(self) -> None:
        self.query_calls = 0

    def embed_texts(self, texts):
        vectors = []
        for text in texts:
            lowered = text.lower()
            vectors.append(
                [
                    1.0 if "first appearance" in lowered or "amazing fantasy #15" in lowered else 0.0,
                    1.0 if "publisher" in lowered or "marvel comics" in lowered else 0.0,
                ]
            )
        return vectors

    def embed_query(self, query_text):
        self.query_calls += 1
        lowered = query_text.lower()
        return [
            1.0 if "first appearance" in lowered or "amazing fantasy #15" in lowered else 0.0,
            1.0 if "publisher" in lowered or "marvel comics" in lowered else 0.0,
        ]


class StubRerankerModel:
    def predict(self, pairs):
        scores = []
        for _, text in pairs:
            lowered = text.lower()
            if "hybrid retrieval" in lowered:
                scores.append(0.95)
            elif "keyword" in lowered:
                scores.append(0.70)
            else:
                scores.append(0.10)
        return scores


class StubLLM:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt, *, system_prompt=None, metadata=None):
        self.calls += 1
        return "Hybrid retrieval combines semantic search with exact keyword matching [1]."


class WikiStubLLM:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt, *, system_prompt=None, metadata=None):
        self.calls += 1
        if "Amazing Fantasy #15" in prompt:
            return "The page lists Spider-Man's first appearance as Amazing Fantasy #15 [1]."
        if "Marvel Comics" in prompt:
            return "The page lists Marvel Comics as the publisher [1]."
        return "The answer is not available from the provided sources."


class RAGPipelineIntegrationTests(unittest.TestCase):
    def test_full_happy_path_with_cached_answer(self) -> None:
        temp_dir = tempfile.mkdtemp()
        pipeline = None
        llm = StubLLM()
        embedder = StubEmbedder()
        try:
            source_path = Path(temp_dir) / "fixture.txt"
            source_path.write_text(
                "Hybrid retrieval combines semantic search and keyword matching.\n\n"
                "Keyword retrieval is useful when exact terms matter.\n\n"
                "Citations should reference chunk positions.",
                encoding="utf-8",
            )
            settings = load_settings(
                config_path="config/config.yaml",
                env_path=".env.example",
                session_overrides={
                    "storage": {
                        "vector_store_path": str(Path(temp_dir) / "vector_db"),
                        "keyword_store_path": str(Path(temp_dir) / "keyword_index"),
                        "metadata_store_path": str(Path(temp_dir) / "processed" / "metadata.json"),
                    }
                },
            )
            pipeline = RAGPipeline.from_settings(
                settings,
                llm_provider=llm,
                embedder=embedder,
                reranker=CrossEncoderReranker(model=StubRerankerModel()),
                session_manager=SessionManager(),
                cache_manager=CacheManager(),
            )

            pipeline.ingest_source(source=str(source_path), source_type="text", session_id="session-1")
            response_one = pipeline.ask(question="What is hybrid retrieval?", session_id="session-1")
            response_two = pipeline.ask(question="What is hybrid retrieval?", session_id="session-1")

            self.assertIn("Citations:", response_one.answer)
            self.assertTrue(response_one.sources)
            self.assertEqual(llm.calls, 1)
            self.assertEqual(embedder.query_calls, 1)
            self.assertEqual(response_two.answer, response_one.answer)
        finally:
            pipeline = None
            gc.collect()
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_cache_key_changes_when_session_overrides_change(self) -> None:
        temp_dir = tempfile.mkdtemp()
        pipeline = None
        llm = StubLLM()
        try:
            source_path = Path(temp_dir) / "fixture.txt"
            source_path.write_text(
                "Hybrid retrieval combines semantic search and keyword matching.",
                encoding="utf-8",
            )
            settings = load_settings(
                config_path="config/config.yaml",
                env_path=".env.example",
                session_overrides={
                    "storage": {
                        "vector_store_path": str(Path(temp_dir) / "vector_db"),
                        "keyword_store_path": str(Path(temp_dir) / "keyword_index"),
                        "metadata_store_path": str(Path(temp_dir) / "processed" / "metadata.json"),
                    }
                },
            )
            session_manager = SessionManager()
            pipeline = RAGPipeline.from_settings(
                settings,
                llm_provider=llm,
                embedder=StubEmbedder(),
                reranker=CrossEncoderReranker(model=StubRerankerModel()),
                session_manager=session_manager,
                cache_manager=CacheManager(),
            )

            pipeline.ingest_source(source=str(source_path), source_type="text", session_id="session-1")
            session_manager.set_settings_overrides("session-1", {"generation": {"model_name": "gemini-2.5-flash"}})
            pipeline.ask(question="What is hybrid retrieval?", session_id="session-1")
            session_manager.set_settings_overrides("session-1", {"generation": {"model_name": "gemini-2.5-pro"}})
            pipeline.ask(question="What is hybrid retrieval?", session_id="session-1")

            self.assertEqual(llm.calls, 2)
        finally:
            pipeline = None
            gc.collect()
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_url_ingestion_with_infobox_supports_first_appearance_question(self) -> None:
        temp_dir = tempfile.mkdtemp()
        pipeline = None
        try:
            settings = load_settings(
                config_path="config/config.yaml",
                env_path=".env.example",
                session_overrides={
                    "storage": {
                        "vector_store_path": str(Path(temp_dir) / "vector_db"),
                        "keyword_store_path": str(Path(temp_dir) / "keyword_index"),
                        "metadata_store_path": str(Path(temp_dir) / "processed" / "metadata.json"),
                    }
                },
            )
            pipeline = RAGPipeline.from_settings(
                settings,
                llm_provider=WikiStubLLM(),
                embedder=WikiStubEmbedder(),
                reranker=CrossEncoderReranker(model=StubRerankerModel()),
                session_manager=SessionManager(),
                cache_manager=CacheManager(),
            )

            html = """
            <html>
              <head><title>Spider-Man</title></head>
              <body>
                <main>
                  <table class="infobox">
                    <tr><th>Publisher</th><td>Marvel Comics</td></tr>
                    <tr><th>First appearance</th><td>Amazing Fantasy #15 (August 1962)</td></tr>
                  </table>
                  <h1>Spider-Man</h1>
                  <p>Spider-Man is a superhero appearing in Marvel Comics.</p>
                </main>
              </body>
            </html>
            """
            response = Mock()
            response.text = html
            response.raise_for_status = Mock()

            with patch("src.ingestion.loaders.url_loader.requests.get", return_value=response):
                pipeline.ingest_source(
                    source="https://example.com/spider-man",
                    source_type="url",
                    session_id="session-1",
                )

            answer = pipeline.ask(
                question="Is Spider-Man's first appearance listed as Amazing Fantasy #15 or The Amazing Spider-Man #1?",
                session_id="session-1",
            )

            self.assertIn("Amazing Fantasy #15", answer.answer)
            self.assertTrue(any("Amazing Fantasy #15" in citation.snippet for citation in answer.sources))
        finally:
            pipeline = None
            gc.collect()
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
