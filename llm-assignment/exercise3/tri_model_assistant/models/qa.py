from __future__ import annotations

from dataclasses import dataclass
import logging
import os
import re

from tri_model_assistant.core.config import AppConfig

LOGGER = logging.getLogger(__name__)


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "can",
    "did",
    "do",
    "does",
    "for",
    "from",
    "give",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "or",
    "please",
    "tell",
    "the",
    "this",
    "to",
    "was",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "you",
    "your",
}
DOCUMENT_ANALYSIS_TERMS = {
    "audience",
    "benefit",
    "benefits",
    "challenge",
    "challenges",
    "conclusion",
    "conclusions",
    "context",
    "document",
    "finding",
    "findings",
    "gist",
    "goal",
    "goals",
    "idea",
    "ideas",
    "issue",
    "issues",
    "key",
    "main",
    "meaning",
    "mentioned",
    "overview",
    "point",
    "points",
    "problem",
    "problems",
    "purpose",
    "risk",
    "risks",
    "solve",
    "solved",
    "solving",
    "subject",
    "summary",
    "takeaway",
    "takeaways",
    "text",
    "theme",
    "themes",
    "topic",
    "topics",
}
SELF_REFERENTIAL_PHRASES = (
    "who are you",
    "what are you",
    "who made you",
    "who created you",
)
BROAD_DOCUMENT_QUESTION_PHRASES = (
    "main idea",
    "main ideas",
    "key idea",
    "key ideas",
    "main point",
    "main points",
    "key point",
    "key points",
    "gist",
    "overview",
    "what is this about",
    "what is the document about",
    "what is the text about",
)
INSUFFICIENT_INFORMATION_MARKERS = (
    "does not contain enough information",
    "not contain enough information",
    "not enough information",
    "insufficient information",
)
OUT_OF_SCOPE_REFUSAL = (
    "I can only answer questions grounded in the stored document context. "
    "That request is outside the document, so I can't answer it here."
)


@dataclass(slots=True)
class QAResponse:
    question: str
    answer: str


def should_refuse_question(context: str, question: str) -> bool:
    normalized_question = " ".join(question.strip().lower().split())
    if any(phrase in normalized_question for phrase in SELF_REFERENTIAL_PHRASES):
        return True

    query_tokens = _meaningful_tokens(question)
    if not query_tokens:
        return False

    context_tokens = _meaningful_tokens(context)
    overlap = query_tokens & context_tokens
    if overlap:
        return False

    off_topic_tokens = query_tokens - DOCUMENT_ANALYSIS_TERMS
    return len(off_topic_tokens) >= max(1, len(query_tokens) // 2)


def _meaningful_tokens(text: str) -> set[str]:
    return {token for token in TOKEN_PATTERN.findall(text.lower()) if token not in STOPWORDS}


def is_broad_document_question(question: str) -> bool:
    normalized_question = " ".join(question.strip().lower().split())
    return any(phrase in normalized_question for phrase in BROAD_DOCUMENT_QUESTION_PHRASES)


def looks_like_insufficient_answer(answer: str) -> bool:
    normalized_answer = " ".join(answer.strip().lower().split())
    return any(marker in normalized_answer for marker in INSUFFICIENT_INFORMATION_MARKERS)


def build_grounded_fallback_answer(context: str, question: str) -> str | None:
    if not is_broad_document_question(question):
        return None

    current_summary = _extract_context_section(context, "Current summary:")
    if current_summary:
        return current_summary

    draft_summary = _extract_context_section(context, "Draft summary:")
    if draft_summary:
        return draft_summary

    original_document = _extract_context_section(context, "Original document:")
    if not original_document:
        return None

    sentences = [sentence.strip() for sentence in SENTENCE_SPLIT_PATTERN.split(original_document) if sentence.strip()]
    if not sentences:
        return None

    return " ".join(sentences[:3]).strip()


def _extract_context_section(context: str, label: str) -> str | None:
    if label not in context:
        return None

    start = context.index(label) + len(label)
    next_headers = ("\n\nCurrent summary:\n", "\n\nDraft summary:\n", "\n\nOriginal document:\n")
    end_positions = [context.find(header, start) for header in next_headers if context.find(header, start) != -1]
    end = min(end_positions) if end_positions else len(context)
    extracted = context[start:end].strip()
    return extracted or None


class HuggingFaceQAClient:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._model = None
        self._tokenizer = None

    @property
    def model_name(self) -> str:
        return self._config.qa_model

    def answer_question(self, context: str, question: str) -> QAResponse:
        if should_refuse_question(context=context, question=question):
            return QAResponse(question=question, answer=OUT_OF_SCOPE_REFUSAL)

        model, tokenizer = self._load_model()
        prompt = (
            "Answer the question using only the provided context. "
            "Do not use outside knowledge. "
            "If the context does not contain enough information, reply exactly with: "
            "'The stored document context does not contain enough information to answer that.'\n\n"
            f"Context:\n{context}\n\nQuestion:\n{question}"
        )

        import torch

        try:
            inputs = tokenizer(prompt, return_tensors="pt", max_length=1024, truncation=True)
            with torch.no_grad():
                output_ids = model.generate(
                    inputs["input_ids"],
                    attention_mask=inputs.get("attention_mask"),
                    max_new_tokens=self._config.qa_max_new_tokens,
                    min_new_tokens=self._config.hf_generation_min_new_tokens,
                    do_sample=False,
                    num_beams=4,
                )
            answer = tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()
        except Exception as exc:
            LOGGER.exception("Question answering failed for model %s.", self._config.qa_model)
            raise RuntimeError(
                f"Failed to answer the question with QA model '{self._config.qa_model}'."
            ) from exc

        if looks_like_insufficient_answer(answer):
            fallback_answer = build_grounded_fallback_answer(context=context, question=question)
            if fallback_answer:
                answer = fallback_answer

        return QAResponse(question=question, answer=answer)

    def _load_model(self):
        if self._model is not None and self._tokenizer is not None:
            return self._model, self._tokenizer

        if self._config.hf_local_files_only:
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "transformers is not available. Install requirements from exercise3/requirements.txt first."
            ) from exc

        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self._config.qa_model,
                local_files_only=self._config.hf_local_files_only,
            )
            self._model = AutoModelForSeq2SeqLM.from_pretrained(
                self._config.qa_model,
                local_files_only=self._config.hf_local_files_only,
            )
        except Exception as exc:
            LOGGER.exception("Failed to load QA model %s.", self._config.qa_model)
            raise RuntimeError(
                f"Could not load QA model '{self._config.qa_model}'. "
                "Check that the model name is correct and that required files are available locally."
            ) from exc
        return self._model, self._tokenizer
