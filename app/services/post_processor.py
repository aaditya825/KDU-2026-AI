"""
app/services/post_processor.py
────────────────────────────────
Shared post-processing logic applied after raw text extraction.

Steps:
  1. Clean / normalise raw text.
  2. Generate a ~150-word summary via the LLM adapter.
  3. Extract 5-7 key points via the LLM adapter.
  4. Generate 5-10 topic tags via the LLM adapter.

Prompt templates are read from app/prompts/*.txt at module import time so
the service is not re-reading files on every call.

Low-confidence extractions are surfaced in the ProcessingResult but are
never silently treated as reliable evidence.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from app.adapters.base import LLMAdapter
from app.config.model_registry import (
    DEFAULT_LLM_POSTPROCESS_INPUT_CHARS,
    GENERATION_MAX_TOKENS,
)
from app.models.domain import ExtractionResult, ProcessingResult
from app.services.text_cleaner import clean_text
from app.utils.logging_utils import get_logger
from app.utils.timing import Timer

log = get_logger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_LOW_CONFIDENCE_THRESHOLD = 0.4
_TRUNCATE_CHARS = DEFAULT_LLM_POSTPROCESS_INPUT_CHARS


def _load_prompt(name: str) -> str:
    path = _PROMPTS_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    # Inline fallbacks in case prompt files are missing
    fallbacks = {
        "summary.txt": (
            "Summarize the following content in about 150 words.\n"
            "Keep the meaning accurate and avoid adding unsupported facts.\n\n"
            "Content:\n{content}"
        ),
        "key_points.txt": (
            "Extract 5-7 key points from the following content.\n"
            "Return only a numbered list.\n\n"
            "Content:\n{content}"
        ),
        "topic_tags.txt": (
            "Generate 5-10 short topic tags for the following content.\n"
            "Return only a comma-separated list.\n\n"
            "Content:\n{content}"
        ),
    }
    return fallbacks.get(name, "Summarize:\n{content}")


_SUMMARY_TPL = _load_prompt("summary.txt")
_KEY_POINTS_TPL = _load_prompt("key_points.txt")
_TOPIC_TAGS_TPL = _load_prompt("topic_tags.txt")


def _parse_key_points(raw: str) -> list[str]:
    """Extract numbered or bulleted list items from LLM output."""
    points: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        # Match "1. text", "- text", "* text", "• text"
        m = re.match(r"^(?:\d+[.)]\s*|[-*•]\s+)(.+)$", line)
        if m:
            points.append(m.group(1).strip())
        elif line and not points:
            # Model returned plain sentences instead of a list
            points.append(line)
    return points[:7] if points else [raw.strip()]


def _parse_tags(raw: str) -> list[str]:
    """Split comma-separated tag output and normalise."""
    tags = [t.strip().lower().strip(".,;") for t in raw.split(",")]
    return [t for t in tags if t][:10]


class PostProcessor:
    """
    Orchestrates text cleaning and LLM-based post-processing for one file.
    """

    def __init__(self, llm: LLMAdapter) -> None:
        self._llm = llm

    def process(self, file_id: str, extraction: ExtractionResult) -> ProcessingResult:
        t0 = time.monotonic()

        cleaned = clean_text(extraction.raw_text)
        truncated = cleaned[:_TRUNCATE_CHARS]

        low_conf = extraction.confidence < _LOW_CONFIDENCE_THRESHOLD
        if low_conf:
            log.warning(
                "Low-confidence extraction for file %s (%.2f) — outputs may be unreliable.",
                file_id,
                extraction.confidence,
            )

        summary = self._generate(
            _SUMMARY_TPL.format(content=truncated),
            stage="summary",
            file_id=file_id,
        )
        key_points_raw = self._generate(
            _KEY_POINTS_TPL.format(content=truncated),
            stage="key_points",
            file_id=file_id,
        )
        tags_raw = self._generate(
            _TOPIC_TAGS_TPL.format(content=truncated),
            stage="topic_tags",
            file_id=file_id,
        )

        key_points = _parse_key_points(key_points_raw)
        topic_tags = _parse_tags(tags_raw)

        total_latency = int((time.monotonic() - t0) * 1000)
        log.info(
            "Post-processing complete",
            extra={
                "file_id": file_id,
                "latency_ms": total_latency,
                "low_confidence": low_conf,
            },
        )

        return ProcessingResult(
            file_id=file_id,
            cleaned_text=cleaned,
            summary=summary,
            key_points=key_points,
            topic_tags=topic_tags,
            extraction=extraction,
            latency_ms=total_latency,
        )

    def _generate(self, prompt: str, stage: str, file_id: str) -> str:
        with Timer(f"llm.{stage}") as t:
            try:
                result = self._llm.generate(
                    prompt,
                    max_tokens=GENERATION_MAX_TOKENS.get(stage, 512),
                )
            except Exception as exc:
                log.error(
                    "LLM generation failed",
                    extra={"stage": stage, "file_id": file_id, "error": str(exc)},
                )
                try:
                    from app.adapters.llm_adapter import LocalFallbackAdapter
                    result = LocalFallbackAdapter().generate(
                        prompt,
                        max_tokens=GENERATION_MAX_TOKENS.get(stage, 512),
                    )
                except Exception:
                    result = f"[Fallback unavailable: {exc}]"
        log.debug(
            "LLM stage complete",
            extra={"stage": stage, "file_id": file_id, "latency_ms": t.elapsed_ms},
        )
        return result
