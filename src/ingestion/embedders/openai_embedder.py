"""OpenAI embedder implementation."""

from __future__ import annotations

from collections.abc import Sequence

from src.core.interfaces import Embedder


class OpenAIEmbedder(Embedder):
    def __init__(self, *, model_name: str = "text-embedding-3-small", client: object | None = None) -> None:
        self.model_name = model_name
        self._client = client

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        client = self._get_client()
        response = client.embeddings.create(model=self.model_name, input=list(texts))
        return [list(map(float, item.embedding)) for item in response.data]

    def embed_query(self, query_text: str) -> list[float]:
        return self.embed_texts([query_text])[0]

    def _get_client(self) -> object:
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover - dependency guard.
                raise RuntimeError("openai is required for the OpenAI embedder.") from exc
            self._client = OpenAI()
        return self._client
