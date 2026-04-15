"""Document ingestion pipeline implementation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from src.core.interfaces import Chunker, DocumentLoader, Embedder, KeywordStore, VectorStore
from src.core.models import Chunk, Document
from src.storage.metadata_store import MetadataStore
from src.utils.logger import get_logger
from src.utils.validators import validate_chunk, validate_document


logger = get_logger(__name__)


@dataclass(slots=True)
class IngestionResult:
    document: Document
    chunks: list[Chunk]
    embeddings: list[list[float]]
    chunk_count: int


@dataclass(slots=True)
class IngestionPipeline:
    loaders: Mapping[str, DocumentLoader]
    chunker: Chunker
    embedder: Embedder
    vector_store: VectorStore
    keyword_store: KeywordStore
    metadata_store: MetadataStore

    def ingest_source(self, source: str, source_type: str) -> IngestionResult:
        logger.info("event=ingestion.start source_type=%s", source_type)
        try:
            loader = self.loaders[source_type.lower()]
        except KeyError as exc:
            raise ValueError(f"No loader registered for source type '{source_type}'.") from exc
        document = loader.load(source)
        return self.ingest_document(document)

    def ingest_document(self, document: Document) -> IngestionResult:
        validate_document(document)
        chunks = list(self.chunker.chunk(document))
        if not chunks:
            raise ValueError(f"No chunks generated for document {document.document_id}.")
        logger.info("event=chunking.complete document_id=%s chunk_count=%s", document.document_id, len(chunks))
        for chunk in chunks:
            validate_chunk(chunk)
        embeddings = self.embedder.embed_texts([chunk.text for chunk in chunks])
        if len(embeddings) != len(chunks):
            raise ValueError("Embedding generation did not return one vector per chunk.")

        self.vector_store.delete_document(document.document_id)
        self.keyword_store.delete_document(document.document_id)
        self.metadata_store.delete_document(document.document_id)
        self.vector_store.upsert(chunks, embeddings)
        self.keyword_store.upsert(chunks)
        self.metadata_store.upsert_document(document, chunks)
        logger.info("event=ingestion.persisted document_id=%s chunk_count=%s", document.document_id, len(chunks))

        return IngestionResult(
            document=document,
            chunks=chunks,
            embeddings=embeddings,
            chunk_count=len(chunks),
        )
