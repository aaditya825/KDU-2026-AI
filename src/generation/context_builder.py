"""Builds answer-generation context from retrieved chunks."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.models import RetrievedChunk, SourceCitation
from src.generation.prompts import PromptManager


@dataclass(slots=True)
class ContextBuilder:
    prompt_manager: PromptManager

    def build(self, retrieved_chunks: list[RetrievedChunk]) -> tuple[str, list[SourceCitation]]:
        blocks: list[str] = []
        citations: list[SourceCitation] = []
        for index, item in enumerate(retrieved_chunks, start=1):
            document_title = item.document_title or item.chunk.metadata.get("document_title", item.chunk.document_id)
            source_label = item.document_source or item.chunk.metadata.get("source", "") or item.chunk.document_id
            blocks.append(
                self.prompt_manager.render_context_block(
                    index=index,
                    document_title=document_title,
                    source_label=source_label,
                    chunk_position=item.chunk.position,
                    section_title=item.chunk.section_title,
                    text=item.chunk.text,
                )
            )
            citations.append(
                SourceCitation(
                    document_id=item.chunk.document_id,
                    chunk_id=item.chunk.chunk_id,
                    source=source_label,
                    document_title=document_title,
                    chunk_position=item.chunk.position,
                    snippet=item.chunk.text,
                )
            )
        return "\n\n".join(blocks), citations
