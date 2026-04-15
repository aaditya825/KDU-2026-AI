"""Main RAG orchestration and wiring helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.config import AppSettings
from src.core.models import Query, Response
from src.generation.generator import ResponseGenerator
from src.generation.llms.llm_factory import LLMFactory
from src.ingestion.chunkers.chunker_factory import ChunkerFactory
from src.ingestion.embedders.embedder_factory import EmbedderFactory
from src.ingestion.loaders.loader_factory import LoaderFactory
from src.ingestion.pipeline import IngestionPipeline, IngestionResult
from src.orchestration.cache_manager import CacheManager
from src.orchestration.session_manager import SessionManager
from src.retrieval.pipeline import RetrievalPipeline
from src.retrieval.rerankers.reranker_factory import RerankerFactory
from src.retrieval.retrievers.hybrid_retriever import HybridRetriever
from src.retrieval.retrievers.keyword_retriever import KeywordRetriever
from src.retrieval.retrievers.semantic_retriever import SemanticRetriever
from src.storage.keyword_stores.keyword_store_factory import KeywordStoreFactory
from src.storage.metadata_store import MetadataStore
from src.storage.vector_stores.vector_store_factory import VectorStoreFactory
from src.utils.logger import get_logger


logger = get_logger(__name__)


def _resolve_generation_api_key(settings: AppSettings) -> str | None:
    provider = settings.generation.provider.lower()
    if provider == "gemini":
        return settings.api.gemini_api_key
    if provider == "openai":
        return settings.api.openai_api_key
    return None


@dataclass(slots=True)
class RAGPipeline:
    ingestion_pipeline: IngestionPipeline
    retrieval_pipeline: RetrievalPipeline
    response_generator: ResponseGenerator
    session_manager: SessionManager
    cache_manager: CacheManager

    @classmethod
    def from_settings(
        cls,
        settings: AppSettings,
        *,
        llm_provider: object | None = None,
        embedder: object | None = None,
        reranker: object | None = None,
        session_manager: SessionManager | None = None,
        cache_manager: CacheManager | None = None,
    ) -> "RAGPipeline":
        loaders = LoaderFactory.create_mapping()
        chunker = ChunkerFactory.create(
            settings.chunking.strategy,
            chunk_size=settings.chunking.chunk_size,
            overlap=settings.chunking.overlap,
        )
        embedder_instance = embedder or EmbedderFactory.create(
            settings.embeddings.provider,
            model_name=settings.embeddings.model_name,
            batch_size=settings.embeddings.batch_size,
        )
        vector_store = VectorStoreFactory.create(
            settings.storage.vector_store,
            persist_directory=settings.storage.vector_store_path,
        )
        keyword_store = KeywordStoreFactory.create(
            settings.storage.keyword_store,
            persist_directory=settings.storage.keyword_store_path,
        )
        metadata_store = MetadataStore(storage_path=settings.storage.metadata_store_path)
        ingestion_pipeline = IngestionPipeline(
            loaders=loaders,
            chunker=chunker,
            embedder=embedder_instance,
            vector_store=vector_store,
            keyword_store=keyword_store,
            metadata_store=metadata_store,
        )
        semantic_retriever = SemanticRetriever(
            embedder=embedder_instance,
            vector_store=vector_store,
            top_k=settings.retrieval.semantic_top_k,
        )
        keyword_retriever = KeywordRetriever(
            keyword_store=keyword_store,
            top_k=settings.retrieval.keyword_top_k,
        )
        hybrid_retriever = HybridRetriever(
            semantic_retriever=semantic_retriever,
            keyword_retriever=keyword_retriever,
            fused_top_k=settings.retrieval.fused_top_k,
        )
        reranker_instance = reranker
        if reranker_instance is None and settings.retrieval.reranker_required:
            reranker_instance = RerankerFactory.create(
                settings.retrieval.reranker_name,
            )
        llm_instance = llm_provider or LLMFactory.create(
            settings.generation.provider,
            model_name=settings.generation.model_name,
            temperature=settings.generation.temperature,
            max_tokens=settings.generation.max_tokens,
            request_timeout_seconds=settings.generation.request_timeout_seconds,
            api_key=_resolve_generation_api_key(settings),
        )
        retrieval_pipeline = RetrievalPipeline(
            retriever=hybrid_retriever,
            reranker=reranker_instance,
            rerank_top_k=settings.retrieval.rerank_top_k,
            final_top_k=settings.retrieval.final_top_k,
        )
        return cls(
            ingestion_pipeline=ingestion_pipeline,
            retrieval_pipeline=retrieval_pipeline,
            response_generator=ResponseGenerator(llm_provider=llm_instance),
            session_manager=session_manager or SessionManager(),
            cache_manager=cache_manager or CacheManager(),
        )

    def ingest_source(self, *, source: str, source_type: str, session_id: str) -> IngestionResult:
        logger.info("event=orchestration.ingest.start session_id=%s source_type=%s", session_id, source_type)
        result = self.ingestion_pipeline.ingest_source(source, source_type)
        self.session_manager.add_document(session_id, result.document)
        self._invalidate_session_cache(session_id)
        logger.info(
            "event=orchestration.ingest.complete session_id=%s document_id=%s chunk_count=%s",
            session_id,
            result.document.document_id,
            result.chunk_count,
        )
        return result

    def answer(self, query: Query) -> Response:
        session_state = self.session_manager.get_or_create(query.session_id)
        session_filters = self.session_manager.build_filters(query.session_id, query.filters)
        effective_query = Query(
            query_text=query.query_text,
            top_k=query.top_k,
            filters=session_filters,
            session_id=query.session_id,
            metadata=dict(query.metadata),
        )
        cache_key = self.cache_manager.build_query_key(
            session_id=effective_query.session_id,
            question=effective_query.query_text,
            document_ids=list(session_filters.get("document_id", []))
            if isinstance(session_filters.get("document_id"), list)
            else [],
            filters=session_filters,
            settings_overrides=session_state.settings_overrides,
        )
        cached = self.cache_manager.get(cache_key)
        if isinstance(cached, Response):
            logger.info("event=orchestration.answer.cache_hit session_id=%s", effective_query.session_id)
            return cached

        if not session_filters.get("document_id"):
            response = Response.from_insufficient_context(
                retrieved_chunks=[],
                metadata={
                    "query_text": effective_query.query_text,
                    "user_error": "Upload or ingest at least one source before asking a question.",
                },
            )
            self.session_manager.record_interaction(effective_query.session_id, effective_query, response)
            return response

        logger.info("event=orchestration.answer.start session_id=%s", effective_query.session_id)
        retrieved_chunks = self.retrieval_pipeline.retrieve(effective_query)
        response = self.response_generator.generate(effective_query, retrieved_chunks)
        self.session_manager.record_interaction(effective_query.session_id, effective_query, response)
        self.cache_manager.set(cache_key, response, session_id=effective_query.session_id)
        logger.info(
            "event=orchestration.answer.complete session_id=%s retrieved_chunks=%s latency_ms=%.2f",
            effective_query.session_id,
            len(response.retrieved_chunks),
            response.latency_ms,
        )
        return response

    def ask(
        self,
        *,
        question: str,
        session_id: str,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> Response:
        return self.answer(
            Query(
                query_text=question,
                top_k=top_k or self.retrieval_pipeline.final_top_k,
                filters=filters or {},
                session_id=session_id,
            )
        )

    def _invalidate_session_cache(self, session_id: str) -> None:
        self.cache_manager.delete_session(session_id)
