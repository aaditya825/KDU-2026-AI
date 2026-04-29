"""
app/adapters/embedding_adapter.py
──────────────────────────────────
EmbeddingAdapter implementations:

  SentenceTransformerAdapter — local, free, primary (all-MiniLM-L6-v2)

Model is loaded once and cached as a module-level singleton so repeated
calls within a session do not reload weights from disk.
"""

from __future__ import annotations

import time
from typing import Optional

from app.adapters.base import EmbeddingAdapter
from app.config.model_registry import DEFAULT_EMBEDDING_MODEL
from app.utils.logging_utils import get_logger

log = get_logger(__name__)

_model_cache: dict[str, object] = {}


class SentenceTransformerAdapter(EmbeddingAdapter):
    """Dense embeddings using Sentence Transformers (local, no API key needed)."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        self._model_name = model_name
        self._model = None  # lazy-loaded

    def _load(self):
        if self._model is None:
            if self._model_name in _model_cache:
                self._model = _model_cache[self._model_name]
            else:
                try:
                    from sentence_transformers import SentenceTransformer
                except ImportError as exc:
                    raise RuntimeError(
                        f"sentence-transformers not installed: {exc}"
                    ) from exc
                log.info("Loading embedding model '%s' …", self._model_name)
                self._model = SentenceTransformer(self._model_name)
                _model_cache[self._model_name] = self._model
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        t0 = time.monotonic()
        model = self._load()
        embeddings = model.encode(texts, batch_size=32, show_progress_bar=False)
        latency = int((time.monotonic() - t0) * 1000)
        log.info(
            "Embeddings computed",
            extra={"n": len(texts), "latency_ms": latency},
        )
        return [emb.tolist() for emb in embeddings]

    def embed_query(self, query: str) -> list[float]:
        result = self.embed_texts([query])
        return result[0] if result else []


def build_embedding_adapter(model_name: str = DEFAULT_EMBEDDING_MODEL) -> EmbeddingAdapter:
    return SentenceTransformerAdapter(model_name=model_name)
