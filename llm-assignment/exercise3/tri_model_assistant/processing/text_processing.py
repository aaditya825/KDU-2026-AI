from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from tri_model_assistant.core.config import SummaryLength


PARAGRAPH_BREAK_PATTERN = re.compile(r"\n\s*\n")
INTERNAL_WHITESPACE_PATTERN = re.compile(r"[ \t]+")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")
REFINEMENT_WORD_BOUNDS = {
    SummaryLength.SHORT: (15, 30),
    SummaryLength.MEDIUM: (35, 60),
    SummaryLength.LONG: (70, 110),
}


@dataclass(slots=True)
class Chunk:
    index: int
    text: str
    word_count: int


def normalize_text(text: str) -> str:
    stripped = text.strip()
    stripped = stripped.replace("\r\n", "\n").replace("\r", "\n")
    normalized_lines = [INTERNAL_WHITESPACE_PATTERN.sub(" ", line).strip() for line in stripped.split("\n")]
    return "\n".join(normalized_lines).strip()


def split_paragraphs(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    return [paragraph.strip() for paragraph in PARAGRAPH_BREAK_PATTERN.split(normalized) if paragraph.strip()]


def word_count(text: str) -> int:
    return len(text.split())


def chunk_paragraphs(
    paragraphs: Iterable[str],
    max_words_per_chunk: int,
    overlap_paragraphs: int = 0,
) -> list[Chunk]:
    paragraph_list = [paragraph.strip() for paragraph in paragraphs if paragraph.strip()]
    if not paragraph_list:
        return []

    chunks: list[Chunk] = []
    current_paragraphs: list[str] = []
    current_word_count = 0

    for paragraph in paragraph_list:
        paragraph_word_count = word_count(paragraph)
        chunk_is_full = current_paragraphs and current_word_count + paragraph_word_count > max_words_per_chunk

        if chunk_is_full:
            chunk_text = "\n\n".join(current_paragraphs)
            chunks.append(Chunk(index=len(chunks), text=chunk_text, word_count=current_word_count))

            if overlap_paragraphs > 0:
                current_paragraphs = current_paragraphs[-overlap_paragraphs:]
                current_word_count = sum(word_count(existing) for existing in current_paragraphs)
            else:
                current_paragraphs = []
                current_word_count = 0

        current_paragraphs.append(paragraph)
        current_word_count += paragraph_word_count

    if current_paragraphs:
        chunk_text = "\n\n".join(current_paragraphs)
        chunks.append(Chunk(index=len(chunks), text=chunk_text, word_count=current_word_count))

    return chunks


def chunk_text(text: str, max_words_per_chunk: int, overlap_paragraphs: int = 0) -> list[Chunk]:
    return chunk_paragraphs(
        paragraphs=split_paragraphs(text),
        max_words_per_chunk=max_words_per_chunk,
        overlap_paragraphs=overlap_paragraphs,
    )


def refinement_word_bounds(summary_length: SummaryLength) -> tuple[int, int]:
    return REFINEMENT_WORD_BOUNDS[summary_length]


def is_summary_within_word_bounds(text: str, min_words: int, max_words: int) -> bool:
    count = word_count(normalize_text(text))
    return min_words <= count <= max_words


def truncate_text_to_word_limit(text: str, max_words: int) -> str:
    normalized = normalize_text(text)
    if word_count(normalized) <= max_words:
        return normalized

    sentences = [sentence.strip() for sentence in SENTENCE_SPLIT_PATTERN.split(normalized) if sentence.strip()]
    selected: list[str] = []
    current_words = 0
    for sentence in sentences:
        sentence_word_count = word_count(sentence)
        if not selected and sentence_word_count > max_words:
            break
        if current_words + sentence_word_count > max_words:
            break
        selected.append(sentence)
        current_words += sentence_word_count

    if selected:
        return " ".join(selected).strip()

    return " ".join(normalized.split()[:max_words]).strip()


def coerce_summary_to_word_bounds(
    summary_text: str,
    source_text: str,
    min_words: int,
    max_words: int,
) -> str:
    normalized_summary = normalize_text(summary_text)
    if is_summary_within_word_bounds(normalized_summary, min_words=min_words, max_words=max_words):
        return normalized_summary

    summary_word_count = word_count(normalized_summary)
    if summary_word_count > max_words:
        return truncate_text_to_word_limit(normalized_summary, max_words=max_words)

    normalized_source = normalize_text(source_text)
    source_word_count = word_count(normalized_source)
    if source_word_count <= max_words:
        return normalized_source

    target_words = min(max_words, max(min_words, source_word_count))
    return truncate_text_to_word_limit(normalized_source, max_words=target_words)


def build_refinement_prompt(draft_summary: str, summary_length: SummaryLength, strict: bool = False) -> str:
    min_words, max_words = refinement_word_bounds(summary_length)
    instructions = {
        SummaryLength.SHORT: (
            "Rewrite the summary into a short version with only the essential facts. "
            "Use 1 to 2 sentences and target roughly 15 to 30 words."
        ),
        SummaryLength.MEDIUM: (
            "Rewrite the summary into a medium-length version with balanced detail and readability. "
            "Use 2 to 4 sentences and target roughly 35 to 60 words. "
            "It must be longer than the short version."
        ),
        SummaryLength.LONG: (
            "Rewrite the summary into a longer version with more detail while staying faithful to the source summary. "
            "Use 4 to 6 sentences and target roughly 70 to 110 words. "
            "It must be the most detailed version."
        ),
    }
    instruction = instructions[summary_length]
    strict_instruction = (
        f"Follow the target length strictly. The answer must stay between {min_words} and {max_words} words. "
        "Return only the rewritten summary."
    )
    return (
        f"{instruction}\n"
        f"{strict_instruction if strict else ''}\n"
        "Keep the output factual, self-contained, and faithful to the source summary. "
        "Do not add outside information.\n\n"
        f"Summary:\n{draft_summary}"
    )


def extractive_summary_from_source(source_text: str, summary_length: SummaryLength) -> str:
    normalized_source = normalize_text(source_text)
    if not normalized_source:
        return ""

    min_words, max_words = refinement_word_bounds(summary_length)
    sentences = [sentence.strip() for sentence in SENTENCE_SPLIT_PATTERN.split(normalized_source) if sentence.strip()]

    if not sentences:
        return truncate_text_to_word_limit(normalized_source, max_words=max_words)

    sentence_targets = {
        SummaryLength.SHORT: 2,
        SummaryLength.MEDIUM: 4,
        SummaryLength.LONG: 6,
    }
    max_sentences = sentence_targets[summary_length]

    selected_sentences: list[str] = []
    for sentence in sentences:
        selected_sentences.append(sentence)
        current_summary = " ".join(selected_sentences).strip()
        if len(selected_sentences) >= max_sentences and word_count(current_summary) >= min_words:
            break

    candidate = " ".join(selected_sentences).strip()
    return coerce_summary_to_word_bounds(
        summary_text=candidate,
        source_text=normalized_source,
        min_words=min_words,
        max_words=max_words,
    )
