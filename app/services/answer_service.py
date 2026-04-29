"""
app/services/answer_service.py
────────────────────────────────
Grounded Q&A service.

Enforces strict grounding:
  - The user question is NEVER sent to the LLM without retrieved context.
  - If retrieved chunks do not provide enough evidence, the service returns
    an AnswerResult with insufficient_evidence=True instead of hallucinating.
  - Low-confidence chunks are included in context but labelled as uncertain.

Flow:
  1. Receive question + retrieved SearchResult objects from SearchService.
  2. Filter out zero-score chunks.
  3. Build a context block from chunk texts.
  4. Call LLMAdapter with the grounded Q&A prompt.
  5. Detect "insufficient evidence" responses and set the flag accordingly.
"""

from __future__ import annotations

import time
from pathlib import Path

from app.adapters.base import LLMAdapter
from app.config.model_registry import DEFAULT_QA_CONTEXT_CHARS, GENERATION_MAX_TOKENS
from app.models.domain import AnswerResult, SearchResult
from app.utils.logging_utils import get_logger

log = get_logger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_LOW_CONF_THRESHOLD = 0.4
_VERY_LOW_CONF_THRESHOLD = 0.2
_MIN_SCORE_THRESHOLD = 0.05   # discard near-zero cosine similarity hits
_INSUFFICIENT_MARKERS = [
    "insufficient evidence",
    "context does not",
    "not enough information",
    "cannot answer",
    "no information",
]


def _load_qa_prompt() -> str:
    path = _PROMPTS_DIR / "grounded_qa.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return (
        "Answer the following question using ONLY the provided context chunks.\n"
        "If the context does not contain enough information to answer, respond with:\n"
        "\"Insufficient evidence in the provided context.\"\n\n"
        "Do not use any outside knowledge. Cite the chunk index where possible.\n\n"
        "Question:\n{question}\n\nContext:\n{context}"
    )


_QA_PROMPT_TPL = _load_qa_prompt()


def _build_context(chunks: list[SearchResult]) -> str:
    parts: list[str] = []
    total_chars = 0
    for chunk in chunks:
        label = f"[Chunk #{chunk.chunk_index}]"
        if chunk.confidence < _LOW_CONF_THRESHOLD:
            label += " [LOW CONFIDENCE - treat with caution]"
        part = f"{label}\n{chunk.chunk_text}"
        remaining = DEFAULT_QA_CONTEXT_CHARS - total_chars
        if remaining <= 0:
            break
        if len(part) > remaining:
            part = part[:remaining].rstrip() + "\n[TRUNCATED TO FIT CONTEXT LIMIT]"
        parts.append(part)
        total_chars += len(part)
    return "\n\n---\n\n".join(parts)


class AnswerService:
    """Generate grounded answers from retrieved document chunks."""

    def __init__(self, llm: LLMAdapter) -> None:
        self._llm = llm

    @staticmethod
    def _dedupe_chunks(chunks: list[SearchResult]) -> list[SearchResult]:
        seen: set[tuple[str, int, str]] = set()
        deduped: list[SearchResult] = []
        for chunk in chunks:
            key = (chunk.file_id, chunk.chunk_index, chunk.chunk_text[:120])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(chunk)
        return deduped

    def answer(self, question: str, retrieved_chunks: list[SearchResult]) -> AnswerResult:
        """
        Generate an answer grounded in *retrieved_chunks*.

        Returns an AnswerResult with insufficient_evidence=True if the context
        cannot support the answer.
        """
        relevant = [c for c in retrieved_chunks if c.score >= _MIN_SCORE_THRESHOLD]
        relevant = [
            c for c in relevant
            if c.confidence >= _VERY_LOW_CONF_THRESHOLD
            or "[LOW CONFIDENCE]" in c.chunk_text
        ]
        relevant = self._dedupe_chunks(relevant)

        if not relevant:
            return AnswerResult(
                answer="Insufficient evidence in the provided context.",
                supporting_chunks=[],
                confidence_notes="No relevant chunks were retrieved for this question.",
                insufficient_evidence=True,
            )

        context = _build_context(relevant)
        prompt = _QA_PROMPT_TPL.format(question=question, context=context)

        t0 = time.monotonic()
        try:
            raw_answer = self._llm.generate(
                prompt,
                max_tokens=GENERATION_MAX_TOKENS["answer"],
            )
        except Exception as exc:
            log.error("LLM answer generation failed: %s", exc)
            try:
                from app.adapters.llm_adapter import LocalFallbackAdapter
                raw_answer = LocalFallbackAdapter().generate(
                    prompt,
                    max_tokens=GENERATION_MAX_TOKENS["answer"],
                )
            except Exception:
                raw_answer = "Insufficient evidence in the provided context."
            return AnswerResult(
                answer=raw_answer,
                supporting_chunks=relevant,
                confidence_notes="Primary LLM call failed; local fallback answer was used.",
                insufficient_evidence=True,
            )
        latency = int((time.monotonic() - t0) * 1000)

        insufficient = any(m in raw_answer.lower() for m in _INSUFFICIENT_MARKERS)
        has_low_conf = any(c.confidence < _LOW_CONF_THRESHOLD for c in relevant)
        notes = ""
        if has_low_conf:
            notes = (
                "Some supporting chunks had low extraction confidence. "
                "Verify key facts against the original document."
            )

        log.info(
            "Answer generated",
            extra={
                "insufficient": insufficient,
                "supporting_chunks": len(relevant),
                "latency_ms": latency,
            },
        )
        return AnswerResult(
            answer=raw_answer,
            supporting_chunks=relevant,
            confidence_notes=notes,
            insufficient_evidence=insufficient,
        )

