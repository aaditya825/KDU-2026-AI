"""Prompt selection and rendering helpers."""

from __future__ import annotations

from src.generation.prompts.contextual_prompts import CITATION_LINE_TEMPLATE, CONTEXT_BLOCK_TEMPLATE
from src.generation.prompts.qa_prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


class PromptManager:
    """Renders prompts for the generation layer."""

    def render_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def render_context_block(
        self,
        *,
        index: int,
        document_title: str,
        source_label: str,
        chunk_position: int,
        section_title: str,
        text: str,
    ) -> str:
        return CONTEXT_BLOCK_TEMPLATE.format(
            index=index,
            document_title=document_title,
            source_label=source_label,
            chunk_position=chunk_position,
            section_title=section_title,
            text=text,
        )

    def render_user_prompt(self, *, question: str, context: str) -> str:
        return USER_PROMPT_TEMPLATE.format(question=question, context=context)

    def render_citation_line(self, *, index: int, document_title: str, source_label: str, chunk_position: int) -> str:
        return CITATION_LINE_TEMPLATE.format(
            index=index,
            document_title=document_title,
            source_label=source_label,
            chunk_position=chunk_position,
        )
