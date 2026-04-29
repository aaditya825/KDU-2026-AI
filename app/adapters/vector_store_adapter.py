"""
app/adapters/vector_store_adapter.py
──────────────────────────────────────
VectorStore implementations:

  ChromaVectorStore — local persistent vector DB (default)

Chroma collections are keyed by file_id so each file's chunks live in an
isolated namespace and can be deleted or re-indexed independently.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path

from app.models.domain import SearchResult, TextChunk
from app.utils.logging_utils import get_logger

log = get_logger(__name__)


class VectorStore(ABC):
    @abstractmethod
    def add_chunks(
        self,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
        file_id: str,
    ) -> None: ...

    @abstractmethod
    def search(
        self,
        file_id: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[SearchResult]: ...

    @abstractmethod
    def delete_file(self, file_id: str) -> None: ...

    @abstractmethod
    def count(self, file_id: str) -> int: ...


class ChromaVectorStore(VectorStore):
    """
    Chroma-backed vector store with one collection per file.

    Collections are named ``cas_{file_id}`` to avoid name collisions.
    """

    def __init__(self, persist_dir: str | Path = "data/vector_db") -> None:
        self._persist_dir = str(persist_dir)
        self._client = None      # lazy-loaded

    def _get_client(self):
        if self._client is None:
            try:
                import chromadb
            except ImportError as exc:
                raise RuntimeError(
                    f"chromadb not installed — cannot use ChromaVectorStore: {exc}"
                ) from exc
            self._client = chromadb.PersistentClient(path=self._persist_dir)
        return self._client

    def _collection_name(self, file_id: str) -> str:
        # Chroma names must be 3-63 chars and match [a-zA-Z0-9_-]
        safe = file_id.replace("-", "_")[:50]
        return f"cas_{safe}"

    def _get_or_create_collection(self, file_id: str):
        client = self._get_client()
        return client.get_or_create_collection(
            name=self._collection_name(file_id),
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
        file_id: str,
    ) -> None:
        if not chunks:
            return
        t0 = time.monotonic()
        collection = self._get_or_create_collection(file_id)

        # Upsert so re-processing the same file replaces old vectors
        collection.upsert(
            ids=[c.chunk_id for c in chunks],
            documents=[c.text for c in chunks],
            embeddings=embeddings,
            metadatas=[
                {
                    "file_id": c.file_id,
                    "chunk_index": c.chunk_index,
                    "confidence": c.confidence,
                    "file_name": c.metadata.get("file_name", ""),
                    "pages": json.dumps(c.metadata.get("pages", [])),
                    "extraction_method": c.metadata.get("extraction_method", ""),
                    "page_metadata": json.dumps(c.metadata.get("page_metadata", [])),
                }
                for c in chunks
            ],
        )
        latency = int((time.monotonic() - t0) * 1000)
        log.info(
            "Chunks indexed in Chroma",
            extra={"file_id": file_id, "count": len(chunks), "latency_ms": latency},
        )

    def search(
        self,
        file_id: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[SearchResult]:
        t0 = time.monotonic()
        try:
            collection = self._get_or_create_collection(file_id)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, collection.count()),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            log.error("Chroma search failed: %s", exc)
            return []

        latency = int((time.monotonic() - t0) * 1000)
        log.info(
            "Vector search complete",
            extra={"file_id": file_id, "top_k": top_k, "latency_ms": latency},
        )

        search_results: list[SearchResult] = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(docs, metas, dists):
            # Chroma cosine distance → similarity score (1 - distance)
            score = max(0.0, 1.0 - dist)
            search_results.append(
                SearchResult(
                    chunk_text=doc,
                    score=score,
                    file_id=meta.get("file_id", file_id),
                    file_name=meta.get("file_name", ""),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    confidence=float(meta.get("confidence", 1.0)),
                    source_metadata={
                        **dict(meta),
                        "pages": json.loads(meta.get("pages", "[]"))
                        if isinstance(meta.get("pages"), str)
                        else meta.get("pages", []),
                        "page_metadata": json.loads(meta.get("page_metadata", "[]"))
                        if isinstance(meta.get("page_metadata"), str)
                        else meta.get("page_metadata", []),
                    },
                )
            )
        return search_results

    def delete_file(self, file_id: str) -> None:
        client = self._get_client()
        name = self._collection_name(file_id)
        try:
            client.delete_collection(name)
            log.info("Chroma collection deleted", extra={"file_id": file_id})
        except Exception as exc:
            log.warning("Could not delete collection %s: %s", name, exc)

    def count(self, file_id: str) -> int:
        try:
            collection = self._get_or_create_collection(file_id)
            return int(collection.count())
        except Exception:
            return 0


def build_vector_store(
    store_type: str = "chroma",
    persist_dir: str | Path = "data/vector_db",
) -> VectorStore:
    if store_type == "chroma":
        return ChromaVectorStore(persist_dir=persist_dir)
    raise ValueError(f"Unknown vector store type: {store_type!r}")
