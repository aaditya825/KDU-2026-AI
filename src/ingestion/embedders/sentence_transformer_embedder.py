"""Sentence-transformers embedder implementation."""

from __future__ import annotations

from collections.abc import Sequence

from src.core.interfaces import Embedder


class SentenceTransformerEmbedder(Embedder):
    def __init__(
        self,
        *,
        model_name: str = "all-MiniLM-L6-v2",
        batch_size: int = 32,
        model: object | None = None,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = model

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model()
        vectors = model.encode(
            list(texts),
            batch_size=self.batch_size,
            convert_to_numpy=False,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        embeddings = [list(map(float, vector)) for vector in vectors]
        if len(embeddings) != len(texts):
            raise ValueError("Embedding output count did not match input count.")
        return embeddings

    def embed_query(self, query_text: str) -> list[float]:
        if not query_text.strip():
            raise ValueError("query_text must be non-empty.")
        result = self.embed_texts([query_text])[0]
        return result

    def _get_model(self) -> object:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:  # pragma: no cover - dependency guard.
                raise RuntimeError(
                    "sentence-transformers is required for the default embedder."
                ) from exc
            self._model = SentenceTransformer(self.model_name)
        return self._model
