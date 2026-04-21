from __future__ import annotations

from dataclasses import dataclass, field
import re

from tri_model_assistant.core.config import SummaryLength
from tri_model_assistant.core.router import Route
from tri_model_assistant.models.pipeline import SummaryArtifacts
from tri_model_assistant.processing.text_processing import Chunk, chunk_text


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "which",
    "with",
}


@dataclass(slots=True)
class AssistantState:
    original_text: str
    draft_summary: str | None = None
    short_summary: str | None = None
    medium_summary: str | None = None
    long_summary: str | None = None
    current_summary: str | None = None
    current_summary_length: SummaryLength | None = None
    chunk_count: int = 0
    chunk_summaries: list[str] = field(default_factory=list)
    last_route: Route | None = None
    last_response: str | None = None

    def store_draft_summary(self, artifacts: SummaryArtifacts) -> None:
        self.draft_summary = artifacts.draft_summary
        self.chunk_count = len(artifacts.chunks)
        self.chunk_summaries = list(artifacts.chunk_summaries)
        self.current_summary = artifacts.draft_summary
        self.current_summary_length = None

    def store_refined_summary(self, summary_length: SummaryLength, summary: str) -> None:
        if summary_length is SummaryLength.SHORT:
            self.short_summary = summary
        elif summary_length is SummaryLength.MEDIUM:
            self.medium_summary = summary
        else:
            self.long_summary = summary

        self.current_summary = summary
        self.current_summary_length = summary_length

    def get_refined_summary(self, summary_length: SummaryLength) -> str | None:
        if summary_length is SummaryLength.SHORT:
            return self.short_summary
        if summary_length is SummaryLength.MEDIUM:
            return self.medium_summary
        return self.long_summary

    def best_available_context(self) -> tuple[str, str]:
        if self.current_summary:
            return "current_summary", self.current_summary
        if self.draft_summary:
            return "draft_summary", self.draft_summary
        return "original_text", self.original_text

    def build_qa_context(
        self,
        query: str | None = None,
        qa_chunk_word_limit: int = 220,
        qa_chunk_overlap_paragraphs: int = 1,
        qa_max_chunks: int = 3,
    ) -> tuple[str, str]:
        original_context_label = "original_text"
        original_context_text = self.original_text

        if query and qa_chunk_word_limit > 0 and qa_max_chunks > 0:
            selected_chunks = self.select_relevant_original_chunks(
                query=query,
                max_words_per_chunk=qa_chunk_word_limit,
                overlap_paragraphs=qa_chunk_overlap_paragraphs,
                max_chunks=qa_max_chunks,
            )
            if selected_chunks:
                original_context_label = "retrieved_chunks"
                original_context_text = "\n\n".join(
                    f"[Chunk {chunk.index}]\n{chunk.text}" for chunk in selected_chunks
                )

        sections = [f"Original document:\n{original_context_text}"]
        context_sources = [original_context_label]

        if self.current_summary:
            sections.append(f"Current summary:\n{self.current_summary}")
            context_sources.append("current_summary")
        elif self.draft_summary:
            sections.append(f"Draft summary:\n{self.draft_summary}")
            context_sources.append("draft_summary")

        return "+".join(context_sources), "\n\n".join(sections)

    def select_relevant_original_chunks(
        self,
        query: str,
        max_words_per_chunk: int,
        overlap_paragraphs: int,
        max_chunks: int,
    ) -> list[Chunk]:
        chunks = chunk_text(
            text=self.original_text,
            max_words_per_chunk=max_words_per_chunk,
            overlap_paragraphs=overlap_paragraphs,
        )
        if not chunks:
            return []

        if len(chunks) <= max_chunks:
            return chunks

        query_tokens = _meaningful_tokens(query)
        if not query_tokens:
            return chunks[:max_chunks]

        scored_chunks = []
        for chunk in chunks:
            chunk_tokens = _meaningful_tokens(chunk.text)
            overlap_count = len(query_tokens & chunk_tokens)
            scored_chunks.append((overlap_count, chunk.index, chunk))

        scored_chunks.sort(key=lambda item: (item[0], -item[1]), reverse=True)
        top_scored = scored_chunks[:max_chunks]

        if all(score == 0 for score, _, _ in top_scored):
            return chunks[:max_chunks]

        ordered_selection = sorted((chunk for _, _, chunk in top_scored), key=lambda chunk: chunk.index)
        return ordered_selection


def _meaningful_tokens(text: str) -> set[str]:
    return {token for token in TOKEN_PATTERN.findall(text.lower()) if token not in STOPWORDS}
