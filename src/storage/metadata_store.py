"""Persistent document and chunk metadata store."""

from __future__ import annotations

import json
from dataclasses import asdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.core.models import Chunk, Document
from src.utils.helpers import ensure_directory


@dataclass(slots=True)
class MetadataStore:
    """JSON-backed metadata index for documents and chunks."""

    storage_path: str = "data/processed/metadata.json"
    documents: dict[str, Document] = field(default_factory=dict)
    chunks_by_document: dict[str, list[Chunk]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        path = Path(self.storage_path)
        ensure_directory(path.parent)
        self.storage_path = str(path)
        self._load()

    def upsert_document(self, document: Document, chunks: list[Chunk]) -> None:
        self.documents[document.document_id] = document
        self.chunks_by_document[document.document_id] = list(chunks)
        self._persist()

    def get_document(self, document_id: str) -> Document | None:
        return self.documents.get(document_id)

    def get_chunks(self, document_id: str) -> list[Chunk]:
        return list(self.chunks_by_document.get(document_id, []))

    def delete_document(self, document_id: str) -> None:
        self.documents.pop(document_id, None)
        self.chunks_by_document.pop(document_id, None)
        self._persist()

    def _persist(self) -> None:
        payload = {
            "documents": {
                document_id: self._serialize_document(document) for document_id, document in self.documents.items()
            },
            "chunks_by_document": {
                document_id: [self._serialize_chunk(chunk) for chunk in chunks]
                for document_id, chunks in self.chunks_by_document.items()
            },
        }
        Path(self.storage_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load(self) -> None:
        path = Path(self.storage_path)
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.documents = {
            document_id: self._deserialize_document(document_payload)
            for document_id, document_payload in payload.get("documents", {}).items()
        }
        self.chunks_by_document = {
            document_id: [self._deserialize_chunk(chunk_payload) for chunk_payload in chunks]
            for document_id, chunks in payload.get("chunks_by_document", {}).items()
        }

    def _serialize_document(self, document: Document) -> dict[str, object]:
        payload = asdict(document)
        payload["created_at"] = document.created_at.isoformat()
        return payload

    def _deserialize_document(self, payload: dict[str, object]) -> Document:
        return Document(
            document_id=str(payload["document_id"]),
            source_type=str(payload["source_type"]),
            source=str(payload["source"]),
            title=str(payload["title"]),
            content=str(payload["content"]),
            metadata=dict(payload.get("metadata", {})),
            created_at=datetime.fromisoformat(str(payload["created_at"])),
        )

    def _serialize_chunk(self, chunk: Chunk) -> dict[str, object]:
        return asdict(chunk)

    def _deserialize_chunk(self, payload: dict[str, object]) -> Chunk:
        return Chunk(
            chunk_id=str(payload["chunk_id"]),
            document_id=str(payload["document_id"]),
            text=str(payload["text"]),
            position=int(payload["position"]),
            start_offset=int(payload["start_offset"]),
            end_offset=int(payload["end_offset"]),
            section_title=str(payload["section_title"]),
            metadata=dict(payload.get("metadata", {})),
        )
