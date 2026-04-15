"""Chat UI components."""

from __future__ import annotations

try:
    import streamlit as st
except ImportError:  # pragma: no cover - import guard for scaffold validation.
    st = None

from src.orchestration.session_manager import SessionState
from ui.components.metrics_display import render_citations, render_response_errors, render_response_metrics


def render_chat_history(session_state: SessionState, *, show_metrics: bool = False) -> None:
    if st is None:
        return
    st.subheader("Chat")
    for query, response in zip(session_state.queries, session_state.responses):
        with st.chat_message("user"):
            st.write(query.query_text)
        with st.chat_message("assistant"):
            st.markdown(response.answer)
            if show_metrics:
                render_response_metrics(response)
            render_citations(response, key_prefix=f"history-{query.session_id}-{len(query.query_text)}-{response.latency_ms:.0f}")
            render_response_errors(response)


def render_chat_input(*, disabled: bool = False) -> str | None:
    if st is None:
        return None
    return st.chat_input("Ask a question about the ingested sources", disabled=disabled)
