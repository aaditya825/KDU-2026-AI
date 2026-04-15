"""Session settings component."""

from __future__ import annotations

try:
    import streamlit as st
except ImportError:  # pragma: no cover - import guard for scaffold validation.
    st = None

from src.core.config import AppSettings


def render_session_settings(settings: AppSettings) -> dict[str, object]:
    if st is None:
        return {}
    provider_label = settings.generation.provider.capitalize()
    with st.sidebar:
        st.header("Session Settings")
        model_name = st.text_input(f"{provider_label} model", value=settings.generation.model_name)
        temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=float(settings.generation.temperature), step=0.05)
        max_tokens = st.number_input("Max tokens", min_value=100, max_value=4000, value=int(settings.generation.max_tokens), step=50)
        timeout_seconds = st.number_input(
            "Request timeout (seconds)",
            min_value=5.0,
            max_value=300.0,
            value=float(settings.generation.request_timeout_seconds),
            step=5.0,
        )
        show_metrics = st.checkbox("Show metrics", value=settings.ui.show_metrics)
        st.caption(
            f"Retrieval is locked to semantic {settings.retrieval.semantic_top_k}, "
            f"keyword {settings.retrieval.keyword_top_k}, rerank {settings.retrieval.rerank_top_k}, "
            f"final {settings.retrieval.final_top_k}."
        )
    return {
        "generation": {
            "model_name": model_name,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
            "request_timeout_seconds": float(timeout_seconds),
        },
        "ui": {
            "show_metrics": bool(show_metrics),
            "upload_directory": settings.ui.upload_directory,
        },
    }
