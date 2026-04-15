"""Response generation scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.interfaces import LLMProvider
from src.core.models import Query, Response, RetrievedChunk, SourceCitation
from src.generation.context_builder import ContextBuilder
from src.generation.prompts import PromptManager
from src.utils.logger import get_logger
from src.utils.metrics import timed


logger = get_logger(__name__)


@dataclass(slots=True)
class ResponseGenerator:
    llm_provider: LLMProvider
    prompt_manager: PromptManager = field(default_factory=PromptManager)
    context_builder: ContextBuilder | None = None

    def __post_init__(self) -> None:
        if self.context_builder is None:
            self.context_builder = ContextBuilder(prompt_manager=self.prompt_manager)

    def generate(self, query: Query, retrieved_chunks: list[RetrievedChunk]) -> Response:
        if not retrieved_chunks:
            logger.info("event=generation.insufficient_context session_id=%s retrieved_chunks=0", query.session_id)
            return Response.from_insufficient_context(
                retrieved_chunks=[],
                metadata={
                    "query_text": query.query_text,
                    "user_error": "No relevant context was retrieved from the current sources.",
                },
            )

        assert self.context_builder is not None
        with timed() as timer:
            context, citations = self.context_builder.build(retrieved_chunks)
            prompt = self.prompt_manager.render_user_prompt(question=query.query_text, context=context)
            logger.info(
                "event=generation.start session_id=%s retrieved_chunks=%s",
                query.session_id,
                len(retrieved_chunks),
            )
            try:
                answer = self.llm_provider.generate(
                    prompt,
                    system_prompt=self.prompt_manager.render_system_prompt(),
                    metadata={"session_id": query.session_id, "query_text": query.query_text},
                )
            except Exception as exc:
                logger.exception("event=generation.failed session_id=%s", query.session_id)
                return Response(
                    answer="The answer could not be generated because the language model request failed.",
                    sources=citations,
                    retrieved_chunks=retrieved_chunks,
                    latency_ms=timer.elapsed_ms,
                    metadata={
                        "query_text": query.query_text,
                        "error": str(exc),
                        "user_error": "The language model request failed. Check the configured LLM API settings and try again.",
                    },
                )
        final_answer = self._append_citations(answer, citations)
        metadata = {"query_text": query.query_text}
        if final_answer.strip() == "The answer is not available from the provided sources.":
            metadata["insufficient_context"] = True
            logger.info("event=generation.insufficient_context session_id=%s retrieved_chunks=%s", query.session_id, len(retrieved_chunks))
        else:
            logger.info("event=generation.complete session_id=%s citations=%s", query.session_id, len(citations))
        return Response(
            answer=final_answer,
            sources=citations,
            retrieved_chunks=retrieved_chunks,
            latency_ms=timer.elapsed_ms,
            metadata=metadata,
        )

    def _append_citations(self, answer: str, citations: list[SourceCitation]) -> str:
        cleaned = answer.strip()
        if not citations:
            return cleaned
        if cleaned == "The answer is not available from the provided sources.":
            return cleaned
        citation_lines = [
            self.prompt_manager.render_citation_line(
                index=index,
                document_title=citation.document_title or citation.source,
                source_label=citation.source or citation.document_title,
                chunk_position=citation.chunk_position,
            )
            for index, citation in enumerate(citations, start=1)
        ]
        if "Citations:" in cleaned:
            return cleaned
        return f"{cleaned}\n\nCitations:\n" + "\n".join(citation_lines)
