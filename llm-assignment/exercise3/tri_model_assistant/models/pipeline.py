from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from typing import Any

from tri_model_assistant.core.config import AppConfig, SummaryLength
from tri_model_assistant.processing.text_processing import (
    Chunk,
    build_refinement_prompt,
    chunk_text,
    coerce_summary_to_word_bounds,
    is_summary_within_word_bounds,
    refinement_word_bounds,
)

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SummaryArtifacts:
    chunks: list[Chunk]
    chunk_summaries: list[str]
    draft_summary: str


class TriModelModelGateway:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._summarizer: Any | None = None
        self._refiner: Any | None = None

    @property
    def summarizer_model_name(self) -> str:
        return self._config.summarizer_model

    @property
    def refiner_model_name(self) -> str:
        return self._config.refiner_model

    @property
    def qa_chunk_word_limit(self) -> int:
        return self._config.qa_chunk_word_limit

    @property
    def qa_chunk_overlap_paragraphs(self) -> int:
        return self._config.qa_chunk_overlap_paragraphs

    @property
    def qa_max_chunks(self) -> int:
        return self._config.qa_max_chunks

    def generate_draft_summary(self, source_text: str) -> SummaryArtifacts:
        chunks = chunk_text(
            text=source_text,
            max_words_per_chunk=self._config.chunk_word_limit,
            overlap_paragraphs=self._config.chunk_overlap_paragraphs,
        )
        if not chunks:
            raise ValueError("Input text is empty after normalization.")

        chunk_summaries = [self._summarize_chunk(chunk.text) for chunk in chunks]
        draft_summary = "\n".join(chunk_summaries).strip()

        return SummaryArtifacts(
            chunks=chunks,
            chunk_summaries=chunk_summaries,
            draft_summary=draft_summary,
        )

    def refine_summary(self, draft_summary: str, summary_length: SummaryLength) -> str:
        return self._refine_summary(draft_summary=draft_summary, summary_length=summary_length)

    def _summarize_chunk(self, text: str) -> str:
        summarizer = self._load_summarizer()
        tokenizer = summarizer["tokenizer"]
        model = summarizer["model"]

        import torch

        try:
            inputs = tokenizer(text, return_tensors="pt", max_length=1024, truncation=True)

            with torch.no_grad():
                summary_ids = model.generate(
                    inputs["input_ids"],
                    attention_mask=inputs.get("attention_mask"),
                    max_new_tokens=self._config.summarizer_max_new_tokens,
                    min_new_tokens=self._config.hf_generation_min_new_tokens,
                    do_sample=False,
                    num_beams=4,
                )

            summary_text = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            return summary_text.strip()
        except Exception as exc:
            LOGGER.exception("Summarization failed for model %s.", self._config.summarizer_model)
            raise RuntimeError(
                f"Failed to generate a draft summary with model '{self._config.summarizer_model}'."
            ) from exc

    def _refine_summary(self, draft_summary: str, summary_length: SummaryLength) -> str:
        refiner = self._load_refiner()
        tokenizer = refiner["tokenizer"]
        model = refiner["model"]
        min_words, max_words = refinement_word_bounds(summary_length)

        try:
            initial_prompt = build_refinement_prompt(
                draft_summary=draft_summary,
                summary_length=summary_length,
                strict=False,
            )
            refined_text = self._generate_refinement_text(
                tokenizer=tokenizer,
                model=model,
                prompt=initial_prompt,
                summary_length=summary_length,
            )
            if is_summary_within_word_bounds(refined_text, min_words=min_words, max_words=max_words):
                return refined_text

            retry_prompt = build_refinement_prompt(
                draft_summary=draft_summary,
                summary_length=summary_length,
                strict=True,
            )
            retried_text = self._generate_refinement_text(
                tokenizer=tokenizer,
                model=model,
                prompt=retry_prompt,
                summary_length=summary_length,
            )
            if is_summary_within_word_bounds(retried_text, min_words=min_words, max_words=max_words):
                return retried_text

            fallback_source = draft_summary if draft_summary.strip() else (retried_text or refined_text)
            return coerce_summary_to_word_bounds(
                summary_text=retried_text or refined_text,
                source_text=fallback_source,
                min_words=min_words,
                max_words=max_words,
            )
        except Exception as exc:
            LOGGER.exception(
                "Summary refinement failed for model %s and target length %s.",
                self._config.refiner_model,
                summary_length.value,
            )
            raise RuntimeError(
                f"Failed to refine the summary with model '{self._config.refiner_model}'."
            ) from exc

    def _generate_refinement_text(self, tokenizer: Any, model: Any, prompt: str, summary_length: SummaryLength) -> str:
        import torch

        inputs = tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)

        with torch.no_grad():
            output_ids = model.generate(
                inputs["input_ids"],
                attention_mask=inputs.get("attention_mask"),
                max_new_tokens=self._config.refinement_max_new_tokens(summary_length),
                min_new_tokens=self._config.refinement_min_new_tokens(summary_length),
                do_sample=False,
                num_beams=4,
            )

        refined_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return refined_text.strip()

    def _load_summarizer(self) -> Any:
        if self._summarizer is None:
            self._configure_hugging_face_runtime()
            try:
                from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            except ImportError as exc:
                raise RuntimeError(
                    "transformers is not available. Install requirements from exercise3/requirements.txt first."
                ) from exc

            try:
                tokenizer = AutoTokenizer.from_pretrained(
                    self._config.summarizer_model,
                    local_files_only=self._config.hf_local_files_only,
                )
                model = AutoModelForSeq2SeqLM.from_pretrained(
                    self._config.summarizer_model,
                    local_files_only=self._config.hf_local_files_only,
                )
            except Exception as exc:
                LOGGER.exception("Failed to load summarizer model %s.", self._config.summarizer_model)
                raise RuntimeError(
                    f"Could not load summarizer model '{self._config.summarizer_model}'. "
                    "Check that the model name is correct and that required files are available locally."
                ) from exc

            self._summarizer = {
                "model": model,
                "tokenizer": tokenizer,
            }

        return self._summarizer

    def _load_refiner(self) -> Any:
        if self._refiner is None:
            self._configure_hugging_face_runtime()
            try:
                from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            except ImportError as exc:
                raise RuntimeError(
                    "transformers is not available. Install requirements from exercise3/requirements.txt first."
                ) from exc

            try:
                tokenizer = AutoTokenizer.from_pretrained(
                    self._config.refiner_model,
                    local_files_only=self._config.hf_local_files_only,
                )
                model = AutoModelForSeq2SeqLM.from_pretrained(
                    self._config.refiner_model,
                    local_files_only=self._config.hf_local_files_only,
                )
            except Exception as exc:
                LOGGER.exception("Failed to load refiner model %s.", self._config.refiner_model)
                raise RuntimeError(
                    f"Could not load refinement model '{self._config.refiner_model}'. "
                    "Check that the model name is correct and that required files are available locally."
                ) from exc

            self._refiner = {
                "model": model,
                "tokenizer": tokenizer,
            }

        return self._refiner

    def _configure_hugging_face_runtime(self) -> None:
        if self._config.hf_local_files_only:
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
