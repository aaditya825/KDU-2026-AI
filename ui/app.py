"""Streamlit entrypoint for the hybrid-search RAG chatbot."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import streamlit as st
except ImportError:  # pragma: no cover - import guard for scaffold validation.
    st = None

from src.core.config import load_settings
from src.orchestration.cache_manager import CacheManager
from src.orchestration.rag_pipeline import RAGPipeline
from src.orchestration.session_manager import SessionManager
from src.utils.helpers import ensure_directory
from src.utils.logger import configure_logging
from ui.components.chat_interface import render_chat_history, render_chat_input
from ui.components.document_uploader import IngestionRequest, render_active_sources, render_document_inputs
from ui.components.metrics_display import render_citations, render_response_errors, render_response_metrics
from ui.components.settings_panel import render_session_settings


def _get_session_id() -> str:
    assert st is not None
    if "_rag_session_id" not in st.session_state:
        st.session_state["_rag_session_id"] = uuid4().hex
    return str(st.session_state["_rag_session_id"])


def _settings_signature(settings_dict: dict[str, object]) -> str:
    return json.dumps(settings_dict, sort_keys=True, default=str)


def _get_shared_runtime_objects() -> tuple[SessionManager, CacheManager]:
    assert st is not None
    if "_rag_session_manager" not in st.session_state:
        st.session_state["_rag_session_manager"] = SessionManager()
    if "_rag_cache_manager" not in st.session_state:
        st.session_state["_rag_cache_manager"] = CacheManager()
    return st.session_state["_rag_session_manager"], st.session_state["_rag_cache_manager"]


def _get_or_create_pipeline(settings) -> RAGPipeline:
    assert st is not None
    session_manager, cache_manager = _get_shared_runtime_objects()
    signature = _settings_signature(settings.to_dict())
    if st.session_state.get("_rag_pipeline_signature") != signature:
        st.session_state["_rag_pipeline"] = RAGPipeline.from_settings(
            settings,
            session_manager=session_manager,
            cache_manager=cache_manager,
        )
        st.session_state["_rag_pipeline_signature"] = signature
    return st.session_state["_rag_pipeline"]


def _persist_uploaded_pdf(uploaded_file, upload_directory: str, session_id: str) -> str:
    target_dir = ensure_directory(Path(upload_directory) / session_id)
    target_path = target_dir / uploaded_file.name
    target_path.write_bytes(uploaded_file.getbuffer())
    return str(target_path)


def _handle_ingestion_request(pipeline: RAGPipeline, submission: IngestionRequest, settings, session_id: str) -> None:
    assert st is not None
    try:
        if submission.source_type == "pdf":
            if submission.uploaded_file is None:
                st.error("The PDF upload was empty.")
                return
            source = _persist_uploaded_pdf(submission.uploaded_file, settings.ui.upload_directory, session_id)
        else:
            source = submission.source or ""
        result = pipeline.ingest_source(source=source, source_type=submission.source_type, session_id=session_id)
        st.success(f"Ingested {result.document.reference_label()} with {result.chunk_count} chunks.")
        pipeline.session_manager.clear_error(session_id)
    except Exception as exc:
        pipeline.session_manager.set_error(session_id, str(exc))
        st.error(f"Ingestion failed: {exc}")


def _handle_question(pipeline: RAGPipeline, question: str, session_id: str):
    assert st is not None
    try:
        return pipeline.ask(question=question, session_id=session_id)
    except Exception as exc:
        pipeline.session_manager.set_error(session_id, str(exc))
        st.error(f"Question answering failed: {exc}")
        return None


def run_app() -> None:
    if st is None:
        raise RuntimeError("Streamlit is not installed. Install dependencies before running the UI.")

    base_settings = load_settings()
    configure_logging(base_settings.logging.config_path)
    st.set_page_config(page_title=base_settings.ui.page_title, layout="wide")

    overrides = render_session_settings(base_settings)
    settings = load_settings(session_overrides=overrides)
    session_id = _get_session_id()
    pipeline = _get_or_create_pipeline(settings)
    pipeline.session_manager.set_settings_overrides(session_id, overrides)

    st.title(settings.ui.page_title)
    st.caption("Upload a PDF or submit a blog URL, then ask grounded questions over the ingested sources.")

    submission = render_document_inputs()
    if submission is not None:
        _handle_ingestion_request(pipeline, submission, settings, session_id)

    session_state = pipeline.session_manager.get_or_create(session_id)
    render_active_sources(session_state.active_sources)
    if session_state.last_error:
        st.warning(session_state.last_error)

    render_chat_history(session_state, show_metrics=settings.ui.show_metrics)
    question = render_chat_input(disabled=not session_state.active_document_ids)
    if question:
        with st.chat_message("user"):
            st.write(question)
        response = _handle_question(pipeline, question, session_id)
        if response is not None:
            with st.chat_message("assistant"):
                st.markdown(response.answer)
                if settings.ui.show_metrics:
                    render_response_metrics(response)
                render_citations(response, key_prefix=f"current-{session_id}-{len(session_state.responses)}")
                render_response_errors(response)


if __name__ == "__main__":
    run_app()
