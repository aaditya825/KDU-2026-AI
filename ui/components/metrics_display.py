"""Metrics display helpers."""

from __future__ import annotations

try:
    import streamlit as st
except ImportError:  # pragma: no cover - import guard for scaffold validation.
    st = None

from src.core.models import Response


def render_response_metrics(response: Response) -> None:
    if st is None:
        return
    col1, col2, col3 = st.columns(3)
    col1.metric("Latency (ms)", f"{response.latency_ms:.2f}")
    col2.metric("Retrieved Chunks", str(len(response.retrieved_chunks)))
    col3.metric("Citations", str(len(response.sources)))


def render_citations(response: Response, *, key_prefix: str = "citations") -> None:
    if st is None or not response.sources:
        return
    with st.expander("Citations", expanded=True):
        for index, citation in enumerate(response.sources, start=1):
            st.markdown(f"- **{citation.label()}**")
            if citation.snippet:
                line_count = citation.snippet.count("\n") + 1
                height = max(120, min(320, 24 * min(line_count, 12)))
                st.text_area(
                    f"Chunk content {index}",
                    value=citation.snippet,
                    height=height,
                    disabled=True,
                    key=f"{key_prefix}-chunk-{citation.chunk_id}-{index}",
                )


def render_response_errors(response: Response) -> None:
    if st is None:
        return
    message = response.metadata.get("user_error") if isinstance(response.metadata, dict) else None
    if message:
        if response.metadata.get("insufficient_context"):
            st.warning(str(message))
        else:
            st.error(str(message))
