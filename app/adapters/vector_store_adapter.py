"""Vector store adapters."""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path

from app.models.domain import SearchResult, TextChunk
from app.utils.exceptions import RetrievalError
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
    """Chroma-backed vector store with one collection per file."""

    def __init__(self, persist_dir: str | Path = "data/vector_db") -> None:
        self._persist_dir = str(persist_dir)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import chromadb
            except ImportError as exc:
                raise RetrievalError(
                    f"chromadb is not installed; cannot use ChromaVectorStore: {exc}",
                    remediation="Install dependencies or rely on keyword fallback.",
                ) from exc
            try:
                self._client = chromadb.PersistentClient(path=self._persist_dir)
            except Exception as exc:
                raise RetrievalError(
                    "Chroma vector store is unavailable or corrupted.",
                    remediation="Delete data/vector_db to rebuild it from SQLite chunks, then retry.",
                ) from exc
        return self._client

    def _collection_name(self, file_id: str) -> str:
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
        if len(chunks) != len(embeddings):
            raise RetrievalError(
                "Vector indexing failed because chunk and embedding counts do not match."
            )

        t0 = time.monotonic()
        try:
            collection = self._get_or_create_collection(file_id)
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
        except RetrievalError:
            raise
        except Exception as exc:
            raise RetrievalError(
                "Chroma indexing failed.",
                remediation="Keyword fallback will be used; delete data/vector_db to force vector rebuild.",
            ) from exc

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
        if not query_embedding:
            return []
        t0 = time.monotonic()
        try:
            collection = self._get_or_create_collection(file_id)
            collection_count = collection.count()
            if collection_count <= 0:
                return []
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, collection_count),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            log.warning(
                "Chroma search failed; caller should use keyword fallback. Error: %s",
                exc,
            )
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
        except Exception as exc:
            log.warning("Chroma count failed for file %s: %s", file_id, exc)
            return 0


def build_vector_store(
    store_type: str = "chroma",
    persist_dir: str | Path = "data/vector_db",
) -> VectorStore:
    if store_type == "chroma":
        return ChromaVectorStore(persist_dir=persist_dir)
    raise ValueError(f"Unknown vector store type: {store_type!r}")
