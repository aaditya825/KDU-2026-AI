"""Prompt fragments for context assembly."""

CONTEXT_BLOCK_TEMPLATE = """[{index}] {document_title} | {source_label} | chunk {chunk_position}
Section: {section_title}
Content:
{text}"""

CITATION_LINE_TEMPLATE = "- [{index}] {document_title} | {source_label} | chunk {chunk_position}"
