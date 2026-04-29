"""
Embedding adapter implementations.

SentenceTransformerAdapter is the local default. It lazy-loads the model and
raises retrieval-specific errors so callers can fall back to keyword search.
"""

from __future__ import annotations

import time

from app.adapters.base import EmbeddingAdapter
from app.config.model_registry import DEFAULT_EMBEDDING_MODEL
from app.utils.exceptions import RetrievalError
from app.utils.logging_utils import get_logger

log = get_logger(__name__)

_model_cache: dict[str, object] = {}


class SentenceTransformerAdapter(EmbeddingAdapter):
    """Dense embeddings using Sentence Transformers."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        self._model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            if self._model_name in _model_cache:
                self._model = _model_cache[self._model_name]
            else:
                try:
                    from sentence_transformers import SentenceTransformer
                except ImportError as exc:
                    raise RetrievalError(
                        f"sentence-transformers is not installed: {exc}",
                        remediation="Install dependencies or rely on keyword fallback.",
                    ) from exc

                log.info("Loading embedding model '%s' ...", self._model_name)
                try:
                    self._model = SentenceTransformer(self._model_name)
                except Exception as exc:
                    raise RetrievalError(
                        f"Embedding model '{self._model_name}' could not be loaded.",
                        remediation=(
                            "Check network access for first download, local model cache, "
                            "and available memory."
                        ),
                    ) from exc
                _model_cache[self._model_name] = self._model
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        t0 = time.monotonic()
        model = self._load()
        try:
            embeddings = model.encode(texts, batch_size=32, show_progress_bar=False)
        except Exception as exc:
            raise RetrievalError(
                f"Embedding generation failed for model '{self._model_name}'.",
                remediation="Keyword fallback will be used if chunks are available.",
            ) from exc

        latency = int((time.monotonic() - t0) * 1000)
        log.info(
            "Embeddings computed",
            extra={"n": len(texts), "latency_ms": latency},
        )

        try:
            return [emb.tolist() for emb in embeddings]
        except AttributeError as exc:
            raise RetrievalError("Embedding model returned an unsupported vector shape.") from exc

    def embed_query(self, query: str) -> list[float]:
        result = self.embed_texts([query])
        return result[0] if result else []


def build_embedding_adapter(model_name: str = DEFAULT_EMBEDDING_MODEL) -> EmbeddingAdapter:
    return SentenceTransformerAdapter(model_name=model_name)
