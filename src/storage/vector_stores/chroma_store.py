"""ChromaDB-backed persistent vector store."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from chromadb import PersistentClient

from src.core.interfaces import VectorStore
from src.core.models import Chunk, RetrievedChunk
from src.utils.helpers import ensure_directory


class ChromaVectorStore(VectorStore):
    def __init__(self, *, persist_directory: str = "data/vector_db", collection_name: str = "rag_chunks") -> None:
        self.persist_directory = ensure_directory(persist_directory)
        self.collection_name = collection_name
        self._client = PersistentClient(path=str(self.persist_directory))
        self._collection = self._client.get_or_create_collection(name=collection_name)

    def upsert(self, chunks: Sequence[Chunk], embeddings: Sequence[Sequence[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("Chunk and embedding counts must match.")
        if not chunks:
            return

        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [self._serialize_chunk_metadata(chunk) for chunk in chunks]
        self._collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=[list(map(float, embedding)) for embedding in embeddings],
            metadatas=metadatas,
        )

    def delete_document(self, document_id: str) -> None:
        self._collection.delete(where={"document_id": document_id})

    def similarity_search(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int,
        filters: Mapping[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        if top_k <= 0:
            return []
        results = self._collection.query(
            query_embeddings=[list(map(float, query_embedding))],
            n_results=top_k,
            where=self._build_where(filters),
        )
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0] if results.get("distances") else []

        retrieved: list[RetrievedChunk] = []
        for index, chunk_id in enumerate(ids):
            metadata = metadatas[index] if index < len(metadatas) else {}
            document = documents[index] if index < len(documents) else ""
            distance = distances[index] if index < len(distances) else None
            chunk = self._deserialize_chunk(chunk_id, document, metadata)
            score = None if distance is None else 1.0 - float(distance)
            retrieved.append(
                RetrievedChunk(
                    chunk=chunk,
                    retrieval_source="semantic",
                    score=score,
                    raw_scores={"chroma_distance": float(distance)} if distance is not None else {},
                    rank=index + 1,
                    document_title=chunk.metadata.get("document_title"),
                    document_source=chunk.metadata.get("source"),
                )
            )
        return retrieved

    def _serialize_chunk_metadata(self, chunk: Chunk) -> dict[str, Any]:
        return {
            "document_id": chunk.document_id,
            "chunk_id": chunk.chunk_id,
            "position": chunk.position,
            "start_offset": chunk.start_offset,
            "end_offset": chunk.end_offset,
            "section_title": chunk.section_title or "",
            "source": str(chunk.metadata.get("source", "")),
            "source_type": str(chunk.metadata.get("source_type", "")),
            "document_title": str(chunk.metadata.get("document_title", "")),
            "payload_json": json.dumps(chunk.metadata, default=str),
        }

    def _deserialize_chunk(self, chunk_id: str, text: str, metadata: Mapping[str, Any]) -> Chunk:
        payload = metadata.get("payload_json", "{}")
        chunk_metadata = json.loads(payload) if isinstance(payload, str) else {}
        chunk_metadata.setdefault("source", metadata.get("source", ""))
        chunk_metadata.setdefault("source_type", metadata.get("source_type", ""))
        chunk_metadata.setdefault("document_title", metadata.get("document_title", ""))
        return Chunk(
            chunk_id=chunk_id,
            document_id=str(metadata.get("document_id", "")),
            text=text,
            position=int(metadata.get("position", 0)),
            start_offset=int(metadata.get("start_offset", 0)),
            end_offset=int(metadata.get("end_offset", 0)),
            section_title=str(metadata.get("section_title", "")),
            metadata=chunk_metadata,
        )

    def _build_where(self, filters: Mapping[str, Any] | None) -> dict[str, Any] | None:
        if not filters:
            return None
        clauses: list[dict[str, Any]] = []
        for key, value in filters.items():
            if isinstance(value, (str, int, float, bool)):
                clauses.append({key: value})
            elif isinstance(value, (list, tuple, set)):
                membership = [{key: item} for item in value if isinstance(item, (str, int, float, bool))]
                if len(membership) == 1:
                    clauses.append(membership[0])
                elif len(membership) > 1:
                    clauses.append({"$or": membership})
        if not clauses:
            return None
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}
