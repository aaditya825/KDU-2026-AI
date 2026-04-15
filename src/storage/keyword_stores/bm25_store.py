"""Persistent BM25-backed keyword store."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

from src.core.interfaces import KeywordStore
from src.core.models import Chunk, RetrievedChunk
from src.utils.helpers import ensure_directory


class BM25KeywordStore(KeywordStore):
    def __init__(self, *, persist_directory: str = "data/keyword_index", index_filename: str = "bm25_index.json") -> None:
        self.persist_directory = ensure_directory(persist_directory)
        self.index_path = Path(self.persist_directory) / index_filename
        self._records: dict[str, dict[str, Any]] = {}
        self._ordered_chunk_ids: list[str] = []
        self._corpus_tokens: list[list[str]] = []
        self._bm25: BM25Okapi | None = None
        self._load()

    def upsert(self, chunks: Sequence[Chunk]) -> None:
        if not chunks:
            return
        document_ids = {chunk.document_id for chunk in chunks}
        for document_id in document_ids:
            self.delete_document(document_id)

        for chunk in chunks:
            self._records[chunk.chunk_id] = {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "text": chunk.text,
                "position": chunk.position,
                "start_offset": chunk.start_offset,
                "end_offset": chunk.end_offset,
                "section_title": chunk.section_title,
                "metadata": chunk.metadata,
            }
        self._rebuild_index()
        self._persist()

    def delete_document(self, document_id: str) -> None:
        removed = [chunk_id for chunk_id, record in self._records.items() if record["document_id"] == document_id]
        for chunk_id in removed:
            self._records.pop(chunk_id, None)
        self._rebuild_index()
        self._persist()

    def keyword_search(
        self,
        query_text: str,
        *,
        top_k: int,
        filters: Mapping[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        if not query_text.strip() or top_k <= 0 or self._bm25 is None:
            return []

        query_tokens = self._tokenize(query_text)
        scores = self._bm25.get_scores(query_tokens)
        results: list[tuple[float, float, dict[str, Any]]] = []
        for chunk_id, score in zip(self._ordered_chunk_ids, scores):
            record = self._records[chunk_id]
            if not self._matches_filters(record, filters):
                continue
            composite_score = self._score_record(query_text, query_tokens, record, float(score))
            results.append((composite_score, float(score), record))

        results.sort(key=lambda item: (item[0], item[1]), reverse=True)
        retrieved: list[RetrievedChunk] = []
        for rank, (score, bm25_score, record) in enumerate(results[:top_k], start=1):
            chunk = Chunk(
                chunk_id=record["chunk_id"],
                document_id=record["document_id"],
                text=record["text"],
                position=int(record["position"]),
                start_offset=int(record["start_offset"]),
                end_offset=int(record["end_offset"]),
                section_title=record["section_title"],
                metadata=dict(record.get("metadata", {})),
            )
            retrieved.append(
                RetrievedChunk(
                    chunk=chunk,
                    retrieval_source="keyword",
                    score=score,
                    raw_scores={"bm25": bm25_score, "keyword_composite": score},
                    rank=rank,
                    document_title=chunk.metadata.get("document_title"),
                    document_source=chunk.metadata.get("source"),
                )
            )
        return retrieved

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\b\w+\b", text.lower())

    def _score_record(
        self,
        query_text: str,
        query_tokens: list[str],
        record: Mapping[str, Any],
        bm25_score: float,
    ) -> float:
        text = str(record.get("text", "")).lower()
        metadata = record.get("metadata", {})
        section_title = str(record.get("section_title", "")).lower()
        if not text:
            return bm25_score

        informative_tokens = [token for token in query_tokens if token not in {"what", "is", "the", "a", "an", "of", "or", "and", "to", "in", "for", "does", "listed", "as"}]
        if not informative_tokens:
            informative_tokens = query_tokens

        matched_terms = sum(1 for token in informative_tokens if token in text)
        coverage = matched_terms / max(len(informative_tokens), 1)

        phrase_bonus = 0.0
        for size in (3, 2):
            if len(informative_tokens) < size:
                continue
            for index in range(len(informative_tokens) - size + 1):
                phrase = " ".join(informative_tokens[index : index + size])
                if phrase and phrase in text:
                    phrase_bonus = max(phrase_bonus, float(size) * 2.0)

        section_type = str(metadata.get("section_type", "")).lower() if isinstance(metadata, Mapping) else ""
        section_bonus = 0.0
        if section_type == "infobox" or section_title == "summary facts":
            section_bonus += 3.0
        if any(token in section_title for token in informative_tokens):
            section_bonus += 1.0

        exact_query_bonus = 1.0 if query_text.lower().strip("?!. ") in text else 0.0
        return bm25_score + (coverage * 2.5) + phrase_bonus + section_bonus + exact_query_bonus

    def _rebuild_index(self) -> None:
        self._ordered_chunk_ids = list(self._records.keys())
        self._corpus_tokens = [self._tokenize(self._records[chunk_id]["text"]) for chunk_id in self._ordered_chunk_ids]
        self._bm25 = BM25Okapi(self._corpus_tokens) if self._corpus_tokens else None

    def _persist(self) -> None:
        self.index_path.write_text(
            json.dumps({"records": list(self._records.values())}, indent=2, default=str),
            encoding="utf-8",
        )

    def _load(self) -> None:
        if not self.index_path.exists():
            return
        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        for record in data.get("records", []):
            self._records[record["chunk_id"]] = record
        self._rebuild_index()

    def _matches_filters(self, record: Mapping[str, Any], filters: Mapping[str, Any] | None) -> bool:
        if not filters:
            return True
        metadata = record.get("metadata", {})
        for key, value in filters.items():
            record_value = record.get(key)
            metadata_value = metadata.get(key) if isinstance(metadata, Mapping) else None
            if isinstance(value, (list, tuple, set)):
                if record_value in value or metadata_value in value:
                    continue
                return False
            if record_value == value:
                continue
            if isinstance(metadata, Mapping) and metadata_value == value:
                continue
            return False
        return True
