"""
app/controllers/search_controller.py
──────────────────────────────────────
Orchestrates Phase-3 semantic search and grounded Q&A for a single file.

On first search/ask for a file this controller checks whether the file has
already been embedded in Chroma. If not, it runs the chunking + embedding
pipeline automatically so the user doesn't need a separate "embed" step.

All dependencies are built from settings defaults and can be overridden
via constructor arguments (useful for testing).
"""

from __future__ import annotations

import re

from app.adapters.embedding_adapter import build_embedding_adapter
from app.adapters.vector_store_adapter import build_vector_store
from app.config.settings import settings
from app.models.domain import AnswerResult, SearchResult
from app.repositories.file_repository import FileRepository
from app.repositories.processing_repository import ProcessingRepository
from app.services.answer_service import AnswerService
from app.services.chunker import chunk_text
from app.services.search_service import SearchService
from app.utils.logging_utils import get_logger

log = get_logger(__name__)


def _build_llm():
    from app.adapters.llm_adapter import build_llm_adapter
    return build_llm_adapter(
        provider=settings.default_llm_provider,
        model=settings.default_llm_model,
        api_keys={
            "gemini": settings.gemini_api_key,
            "openai": settings.openai_api_key,
        },
    )


class SearchController:
    """Entry point for CLI and (later) Streamlit search/ask flows."""

    def __init__(
        self,
        file_repo: FileRepository | None = None,
        proc_repo: ProcessingRepository | None = None,
        search_service: SearchService | None = None,
        answer_service: AnswerService | None = None,
    ) -> None:
        self._file_repo = file_repo or FileRepository()
        self._proc_repo = proc_repo or ProcessingRepository()

        if search_service is None:
            embedding = build_embedding_adapter(settings.default_embedding_model)
            vector_store = build_vector_store(
                store_type=settings.default_vector_store,
                persist_dir=settings.vector_db_dir,
            )
            self._search_svc = SearchService(embedding, vector_store)
            self._embedding = embedding
            self._vector_store = vector_store
        else:
            self._search_svc = search_service
            # Keep direct handles for indexing from repository-backed chunks.
            self._embedding = search_service._embed
            self._vector_store = search_service._store

        self._answer_svc = answer_service or AnswerService(_build_llm())
        self._semantic_available = True

    def _ensure_indexed(self, file_id: str) -> None:
        """
        Ensure chunks for *file_id* exist in the vector store.

        If the DB has chunks but they haven't been embedded yet, this method
        generates embeddings and indexes them in Chroma.
        """
        chunks = self._proc_repo.get_chunks(file_id)

        if chunks:
            indexed_count = self._vector_store.count(file_id)
            if indexed_count >= len(chunks):
                return

            if not self._semantic_available:
                return

            # Chunks exist in SQLite but vector store is missing/partial.
            texts = [c.text for c in chunks]
            try:
                embeddings = self._embedding.embed_texts(texts)
                self._vector_store.add_chunks(chunks, embeddings, file_id)
                log.info(
                    "Re-indexed existing chunks for file %s (stored=%d, indexed_before=%d).",
                    file_id,
                    len(chunks),
                    indexed_count,
                )
            except Exception as exc:
                self._semantic_available = False
                log.warning(
                    "Could not re-index chunks for file %s; keyword fallback will be used. Error: %s",
                    file_id,
                    exc,
                )
            return

        # No chunks in DB — build them from the processed output
        output = self._proc_repo.get_processing_result(file_id)
        if output is None:
            raise ValueError(
                f"File '{file_id}' has not been processed yet. "
                "Run 'python -m app.cli process <file_id>' first."
            )

        file_meta = self._file_repo.get(file_id)
        file_name = file_meta.original_name if file_meta else ""
        confidence = output.get("confidence", 1.0) or 1.0

        cleaned_text = output.get("cleaned_text", "")
        if not cleaned_text:
            raise ValueError(
                f"Processed output for '{file_id}' contains no text to index."
            )

        log.info("Building chunks and embeddings for file %s …", file_id)
        chunks = chunk_text(
            text=cleaned_text,
            file_id=file_id,
            file_name=file_name,
            confidence=confidence,
            extra_metadata={
                "extraction_method": output.get("extraction_method", "unknown"),
                "page_metadata": output.get("page_metadata", []),
            },
        )

        if not chunks:
            raise ValueError(f"No chunks produced for file '{file_id}'.")

        # Persist chunks even if embedding/indexing fails so keyword fallback can still run.
        self._proc_repo.save_chunks(chunks)

        if not self._semantic_available:
            return

        texts = [c.text for c in chunks]
        try:
            embeddings = self._embedding.embed_texts(texts)
            self._vector_store.add_chunks(chunks, embeddings, file_id)
            log.info("Indexed %d chunks for file %s.", len(chunks), file_id)
        except Exception as exc:
            self._semantic_available = False
            log.warning(
                "Embedding/indexing failed for file %s; keyword fallback will be used. Error: %s",
                file_id,
                exc,
            )

    def _resolve_target_file_ids(self, file_id: str | None) -> list[str]:
        if file_id:
            if not self._file_repo.get(file_id):
                raise ValueError(f"File '{file_id}' not found. Run 'ingest' first.")
            return [file_id]

        file_ids = self._proc_repo.list_queryable_file_ids()
        if not file_ids:
            raise ValueError(
                "No queryable processed documents found. Run 'ingest' and 'process' first."
            )
        return file_ids

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {
            tok for tok in re.findall(r"[a-z0-9]+", text.lower())
            if len(tok) > 1
        }

    def _keyword_search(self, file_id: str, query: str, top_k: int) -> list[SearchResult]:
        chunks = self._proc_repo.get_chunks(file_id)
        if not chunks:
            return []

        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []

        file_meta = self._file_repo.get(file_id)
        file_name = file_meta.original_name if file_meta else ""
        results: list[SearchResult] = []
        for c in chunks:
            c_tokens = self._tokenize(c.text)
            if not c_tokens:
                continue
            overlap = q_tokens.intersection(c_tokens)
            if not overlap:
                continue
            score = len(overlap) / len(q_tokens)
            results.append(
                SearchResult(
                    chunk_text=c.text,
                    score=score,
                    file_id=file_id,
                    file_name=file_name or c.metadata.get("file_name", ""),
                    chunk_index=c.chunk_index,
                    confidence=c.confidence,
                    source_metadata=c.metadata,
                )
            )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    @staticmethod
    def _dedupe_results(results: list[SearchResult]) -> list[SearchResult]:
        seen: set[tuple[str, int, str]] = set()
        deduped: list[SearchResult] = []
        for result in results:
            key = (result.file_id, result.chunk_index, result.chunk_text[:120])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(result)
        return deduped

    @staticmethod
    def _validate_query_limits(query: str, top_k: int) -> None:
        if not query.strip():
            raise ValueError("Query cannot be empty.")
        if len(query) > settings.max_query_chars:
            raise ValueError(
                f"Query is too long ({len(query)} characters). "
                f"Maximum allowed: {settings.max_query_chars} characters."
            )
        if top_k < 1 or top_k > settings.max_retrieval_top_k:
            raise ValueError(
                f"top_k must be between 1 and {settings.max_retrieval_top_k}."
            )

    def search(self, file_id: str | None, query: str, top_k: int = 5) -> list[SearchResult]:
        """
        Semantic search over one file or across all processed files when file_id is None.
        """
        self._validate_query_limits(query, top_k)
        target_ids = self._resolve_target_file_ids(file_id)
        all_hits: list[SearchResult] = []
        per_file_k = max(top_k, 3)
        for fid in target_ids:
            try:
                self._ensure_indexed(fid)
            except ValueError as exc:
                # In all-files mode, skip broken/unqueryable records and continue.
                if file_id is None:
                    log.warning("Skipping file %s during global query: %s", fid, exc)
                    continue
                raise
            if self._semantic_available:
                try:
                    hits = self._search_svc.search(fid, query, top_k=per_file_k)
                except Exception as exc:
                    self._semantic_available = False
                    log.warning(
                        "Semantic search failed for file %s; falling back to keyword search. Error: %s",
                        fid,
                        exc,
                    )
                    hits = []
            else:
                hits = []

            if not hits:
                hits = self._keyword_search(fid, query, top_k=per_file_k)
            all_hits.extend(hits)

        all_hits.sort(key=lambda r: r.score, reverse=True)
        return self._dedupe_results(all_hits)[:top_k]

    def answer(self, file_id: str | None, question: str, top_k: int = 5) -> AnswerResult:
        """Grounded Q&A over one file or all processed files when file_id is None."""
        retrieved = self.search(file_id=file_id, query=question, top_k=top_k)
        return self._answer_svc.answer(question, retrieved)
