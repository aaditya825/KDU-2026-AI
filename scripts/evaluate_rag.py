"""Local evaluation entrypoint for the RAG pipeline."""

from __future__ import annotations

import argparse
import gc
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.config import load_settings
from src.orchestration.rag_pipeline import RAGPipeline
from src.retrieval.rerankers.cross_encoder_reranker import CrossEncoderReranker
from src.utils.logger import configure_logging


class StubEmbedder:
    def embed_texts(self, texts):
        return [[float(len(text)), float(index + 1)] for index, text in enumerate(texts)]

    def embed_query(self, query_text):
        return [float(len(query_text)), 1.0]


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
                scores.append(0.20)
        return scores


class StubLLM:
    def generate(self, prompt, *, system_prompt=None, metadata=None):
        return "Hybrid retrieval combines semantic search with exact keyword matching [1]."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a local RAG evaluation without requiring a real API call.")
    parser.add_argument("--source", help="Optional source path or URL. Defaults to an internal text fixture.")
    parser.add_argument(
        "--source-type",
        choices=["pdf", "url", "text"],
        default="text",
        help="Source type for evaluation. Text is intended only for local smoke validation.",
    )
    parser.add_argument(
        "--question",
        default="What is hybrid retrieval?",
        help="Question to ask after ingestion.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    temp_dir = tempfile.mkdtemp(prefix="rag-eval-")
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
        configure_logging(settings.logging.config_path)
        pipeline = RAGPipeline.from_settings(
            settings,
            llm_provider=StubLLM(),
            embedder=StubEmbedder(),
            reranker=CrossEncoderReranker(model=StubRerankerModel()),
        )

        if args.source:
            source = args.source
            source_type = args.source_type
        else:
            source_path = Path(temp_dir) / "local_eval.txt"
            source_path.write_text(
                "Hybrid retrieval combines semantic similarity and exact keyword matching. "
                "This improves answer grounding when semantic-only search misses precise terms.",
                encoding="utf-8",
            )
            source = str(source_path)
            source_type = "text"

        ingestion_result = pipeline.ingest_source(source=source, source_type=source_type, session_id="eval")
        response = pipeline.ask(question=args.question, session_id="eval")

        print(f"Ingested document: {ingestion_result.document.reference_label()}")
        print(f"Chunks created: {ingestion_result.chunk_count}")
        print(f"Answer:\n{response.answer}")
        print("Citations:")
        for citation in response.sources:
            print(f"  - {citation.label()}")
        print(f"Latency: {response.latency_ms:.2f} ms")
    finally:
        gc.collect()
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
