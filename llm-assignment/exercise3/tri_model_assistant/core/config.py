from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os


class SummaryLength(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"

    @classmethod
    def from_user_value(cls, value: str) -> "SummaryLength":
        normalized = value.strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            valid = ", ".join(member.value for member in cls)
            raise ValueError(f"Invalid summary length '{value}'. Expected one of: {valid}.") from exc


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer.") from exc


@dataclass(slots=True)
class AppConfig:
    summarizer_model: str = os.getenv("EX3_SUMMARIZER_MODEL", "sshleifer/distilbart-cnn-12-6")
    refiner_model: str = os.getenv("EX3_REFINER_MODEL", "google/flan-t5-small")
    qa_model: str = os.getenv("EX3_QA_MODEL", "google/flan-t5-base")
    chunk_word_limit: int = _get_int_env("EX3_CHUNK_WORD_LIMIT", 350)
    chunk_overlap_paragraphs: int = _get_int_env("EX3_CHUNK_OVERLAP_PARAGRAPHS", 1)
    qa_chunk_word_limit: int = _get_int_env("EX3_QA_CHUNK_WORD_LIMIT", 220)
    qa_chunk_overlap_paragraphs: int = _get_int_env("EX3_QA_CHUNK_OVERLAP_PARAGRAPHS", 1)
    qa_max_chunks: int = _get_int_env("EX3_QA_MAX_CHUNKS", 3)
    summarizer_max_new_tokens: int = _get_int_env("EX3_SUMMARIZER_MAX_NEW_TOKENS", 130)
    refinement_min_new_tokens_short: int = _get_int_env("EX3_REFINE_SHORT_MIN_NEW_TOKENS", 8)
    refinement_min_new_tokens_medium: int = _get_int_env("EX3_REFINE_MEDIUM_MIN_NEW_TOKENS", 25)
    refinement_min_new_tokens_long: int = _get_int_env("EX3_REFINE_LONG_MIN_NEW_TOKENS", 60)
    refinement_max_new_tokens_short: int = _get_int_env("EX3_REFINE_SHORT_MAX_NEW_TOKENS", 80)
    refinement_max_new_tokens_medium: int = _get_int_env("EX3_REFINE_MEDIUM_MAX_NEW_TOKENS", 150)
    refinement_max_new_tokens_long: int = _get_int_env("EX3_REFINE_LONG_MAX_NEW_TOKENS", 260)
    qa_max_new_tokens: int = _get_int_env("EX3_QA_MAX_NEW_TOKENS", 180)
    hf_generation_min_new_tokens: int = _get_int_env("EX3_HF_MIN_NEW_TOKENS", 20)
    hf_local_files_only: bool = os.getenv("EX3_HF_LOCAL_FILES_ONLY", "false").strip().lower() in {"1", "true", "yes"}

    def refinement_max_new_tokens(self, summary_length: SummaryLength) -> int:
        mapping = {
            SummaryLength.SHORT: self.refinement_max_new_tokens_short,
            SummaryLength.MEDIUM: self.refinement_max_new_tokens_medium,
            SummaryLength.LONG: self.refinement_max_new_tokens_long,
        }
        return mapping[summary_length]

    def refinement_min_new_tokens(self, summary_length: SummaryLength) -> int:
        mapping = {
            SummaryLength.SHORT: self.refinement_min_new_tokens_short,
            SummaryLength.MEDIUM: self.refinement_min_new_tokens_medium,
            SummaryLength.LONG: self.refinement_min_new_tokens_long,
        }
        return mapping[summary_length]
