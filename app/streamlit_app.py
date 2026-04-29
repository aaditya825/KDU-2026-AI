"""Streamlit UI for the Content Accessibility Suite.

Run:
    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

# Streamlit executes this file by path, so the script directory can become
# sys.path[0]. Add the repository root so absolute imports like app.config work.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st

from app.config.settings import settings
from app.utils.exceptions import format_user_error

settings.configure_logging()

st.set_page_config(
    page_title="Content Accessibility Suite",
    layout="wide",
)

_SUPPORTED_EXTENSIONS = ["pdf", "jpg", "jpeg", "png", "mp3", "wav"]
_SUPPORTED_LABEL = "PDF, JPEG, PNG, MP3, WAV"


@st.cache_resource
def _file_controller():
    from app.controllers.file_controller import FileController

    return FileController()


@st.cache_resource
def _processing_controller():
    from app.controllers.processing_controller import ProcessingController

    return ProcessingController()


@st.cache_resource
def _search_controller():
    from app.controllers.search_controller import SearchController

    return SearchController()


def _file_repo():
    from app.repositories.file_repository import FileRepository

    return FileRepository()


def _proc_repo():
    from app.repositories.processing_repository import ProcessingRepository

    return ProcessingRepository()


def _render_search_result(result, index: int) -> None:
    confidence = result.confidence
    source = result.file_name or result.source_metadata.get("file_name", "unknown")
    pages = result.source_metadata.get("pages") or result.source_metadata.get("page")
    score_label = f"score {result.score:.3f}"
    conf_label = f"conf {confidence:.0%}"
    page_label = f"p.{pages}" if pages else ""
    header_parts = [f"[{index}]", source, score_label, conf_label]
    if page_label:
        header_parts.append(page_label)

    with st.expander(" | ".join(header_parts), expanded=(index == 1)):
        if pages:
            st.caption(f"Source pages: {pages}")
        st.text(result.chunk_text[:700])


def _list_all_files():
    try:
        all_files = _file_repo().list_all()
        queryable_ids = set(_proc_repo().list_queryable_file_ids())
        return all_files, queryable_ids
    except Exception as exc:
        st.error(format_user_error(exc, prefix="Could not load document list"))
        return [], set()


def _sidebar() -> None:
    with st.sidebar:
        st.title("Content Accessibility Suite")
        st.caption("Upload -> Process -> Ask")
        st.divider()

        all_files, queryable_ids = _list_all_files()

        st.subheader("Documents")
        if not all_files:
            st.info("No documents uploaded yet.")
        else:
            for item in all_files:
                ready = item.file_id in queryable_ids
                marker = "[ready]" if ready else "[pending]"
                label = "ready" if ready else item.status.value
                st.markdown(
                    f"{marker} **{item.original_name}**  \n"
                    f"<small style='color:grey'>{item.file_type.value} | {label}</small>",
                    unsafe_allow_html=True,
                )

        st.divider()
        st.caption(f"LLM: {settings.default_llm_provider} / {settings.default_llm_model}")
        gemini_ok = bool(settings.gemini_api_key)
        openai_ok = bool(settings.openai_api_key)
        st.caption(
            f"Gemini key: {'set' if gemini_ok else 'missing'}  "
            f"OpenAI key: {'set' if openai_ok else 'missing'}"
        )
        if not gemini_ok and not openai_ok:
            st.warning("No cloud API keys set. Local fallback will be used.")


def _tab_upload() -> None:
    st.header("Upload & Process")
    st.write(f"Upload one document at a time. Supported types: **{_SUPPORTED_LABEL}**.")
    st.caption(
        "Limits: "
        f"{settings.max_upload_mb} MB per file, "
        f"{settings.max_pdf_pages} PDF pages, "
        f"{settings.max_image_pixels:,} image pixels, "
        f"{settings.max_audio_duration_sec}s audio."
    )

    uploaded = st.file_uploader(
        "Choose a file",
        type=_SUPPORTED_EXTENSIONS,
        accept_multiple_files=False,
        help="File type is detected from content, not extension.",
    )

    if uploaded is None:
        st.info("Upload a file above, then click **Ingest & Process**.")
        return

    st.write(f"**{uploaded.name}** - {uploaded.size:,} bytes")

    if uploaded.size > settings.max_upload_bytes:
        st.error(
            f"File is too large ({uploaded.size / (1024 * 1024):.1f} MB). "
            f"Maximum allowed: {settings.max_upload_mb} MB."
        )
        return
    if not st.button("Ingest & Process", type="primary"):
        return

    tmpdir = tempfile.mkdtemp()
    tmp_path = Path(tmpdir) / uploaded.name
    try:
        try:
            tmp_path.write_bytes(uploaded.getbuffer())
        except OSError as exc:
            st.error(format_user_error(exc, prefix="Upload failed"))
            return

        try:
            with st.spinner("Ingesting file..."):
                file_meta = _file_controller().ingest_file(str(tmp_path))
        except Exception as exc:
            st.error(format_user_error(exc, prefix="Ingestion failed"))
            return

        st.success(
            f"Ingested **{file_meta.original_name}** | "
            f"ID `{file_meta.file_id}` | "
            f"type {file_meta.file_type.value} | MIME {file_meta.mime_type}"
        )

        try:
            with st.spinner("Extracting, summarising, embedding..."):
                result = _processing_controller().process_file(file_meta.file_id)
        except ValueError as exc:
            st.error(format_user_error(exc, prefix="Processing failed"))
            return
        except Exception as exc:
            st.error(format_user_error(exc, prefix="Processing failed"))
            return

        confidence = result.extraction.confidence if result.extraction else 0.0
        method = result.extraction.method.value if result.extraction else "unknown"

        st.success(f"Processing complete - {result.latency_ms} ms")

        col1, col2, col3 = st.columns(3)
        col1.metric("Extraction method", method)
        col2.metric("Confidence", f"{confidence:.0%}")
        col3.metric("Latency", f"{result.latency_ms} ms")

        if result.extraction and result.extraction.warnings:
            for warning in result.extraction.warnings:
                st.warning(warning)

        with st.expander("Extracted text preview"):
            st.text(result.cleaned_text[:1200] if result.cleaned_text else "(no text)")

        with st.expander("Summary"):
            st.write(result.summary or "(no summary)")

        with st.expander("Key points"):
            for point in result.key_points:
                st.markdown(f"- {point}")

        with st.expander("Topic tags"):
            st.write(", ".join(result.topic_tags) if result.topic_tags else "(none)")

        st.info("Document is now queryable. Switch to the **Ask / Search** tab.")
        st.rerun()

    finally:
        try:
            shutil.rmtree(tmpdir)
        except Exception as exc:
            st.warning(format_user_error(exc, prefix="Temporary upload cleanup failed"))


def _tab_ask() -> None:
    st.header("Ask / Search")

    all_files, queryable_ids = _list_all_files()
    queryable_files = [item for item in all_files if item.file_id in queryable_ids]

    if not queryable_files:
        st.warning(
            "No processed documents found. "
            "Upload and process a document in the **Upload & Process** tab first."
        )
        return

    scope_labels = ["All documents"] + [item.original_name for item in queryable_files]
    scope_choice = st.selectbox("Search scope", scope_labels, index=0)

    selected_file_id: str | None = None
    if scope_choice != "All documents":
        selected = next(item for item in queryable_files if item.original_name == scope_choice)
        selected_file_id = selected.file_id

    col_left, col_right = st.columns([3, 1])
    with col_right:
        top_k = st.number_input("Chunks to retrieve", min_value=1, max_value=20, value=5)
        mode = st.radio("Mode", ["Q&A", "Search only"], index=0)

    with col_left:
        placeholder = (
            "e.g. What are the key requirements?"
            if mode == "Q&A"
            else "e.g. booking system requirements"
        )
        question = st.text_input(
            "Question" if mode == "Q&A" else "Search query",
            placeholder=placeholder,
        )

    if not question:
        st.caption("Type a question or search term above and press Enter or click Submit.")
        return

    if not st.button("Submit", type="primary"):
        return

    search_controller = _search_controller()
    scope_desc = f"file '{scope_choice}'" if selected_file_id else "all documents"

    if mode == "Q&A":
        with st.spinner(f"Answering from {scope_desc}..."):
            try:
                answer_result = search_controller.answer(
                    file_id=selected_file_id,
                    question=question,
                    top_k=int(top_k),
                )
            except ValueError as exc:
                st.error(format_user_error(exc, prefix="Q&A failed"))
                return
            except Exception as exc:
                st.error(format_user_error(exc, prefix="Q&A failed"))
                return

        if answer_result.insufficient_evidence:
            st.warning(
                "Insufficient evidence in the processed documents to answer this question. "
                "The answer below may be incomplete."
            )
        else:
            st.success("Answer generated from retrieved context.")

        st.markdown("### Answer")
        st.markdown(answer_result.answer)

        if answer_result.confidence_notes:
            st.caption(f"Note: {answer_result.confidence_notes}")

        st.markdown("### Supporting chunks")
        if answer_result.supporting_chunks:
            for index, chunk in enumerate(answer_result.supporting_chunks, 1):
                _render_search_result(chunk, index)
        else:
            st.info("No supporting chunks returned.")

    else:
        with st.spinner(f"Searching {scope_desc}..."):
            try:
                results = search_controller.search(
                    file_id=selected_file_id,
                    query=question,
                    top_k=int(top_k),
                )
            except ValueError as exc:
                st.error(format_user_error(exc, prefix="Search failed"))
                return
            except Exception as exc:
                st.error(format_user_error(exc, prefix="Search failed"))
                return

        if not results:
            st.info("No relevant chunks found for that query.")
            return

        st.success(f"{len(results)} chunk(s) found")
        for index, result in enumerate(results, 1):
            _render_search_result(result, index)


def _tab_compare() -> None:
    st.header("Model Comparison")
    st.write(
        "Runs summary, key-points, and topic-tag stages across configured LLM providers "
        "for a selected document and records latency, estimated cost, and quality notes."
    )

    all_files, queryable_ids = _list_all_files()
    queryable_files = [item for item in all_files if item.file_id in queryable_ids]

    if not queryable_files:
        st.warning(
            "No processed documents found. "
            "Upload and process a document in the **Upload & Process** tab first."
        )
        return

    file_names = [item.original_name for item in queryable_files]
    choice = st.selectbox("Select document", file_names)
    selected = next(item for item in queryable_files if item.original_name == choice)

    if not st.button("Run Comparison", type="primary"):
        return

    from app.controllers.comparison_controller import ComparisonController

    comparison_controller = ComparisonController()
    with st.spinner(f"Running comparison for {selected.original_name}..."):
        try:
            report = comparison_controller.compare(selected.file_id)
        except ValueError as exc:
            st.error(format_user_error(exc, prefix="Comparison failed"))
            return
        except Exception as exc:
            st.error(format_user_error(exc, prefix="Comparison failed"))
            return

    st.success("Comparison complete")

    summary = report.metric_summary
    if summary:
        col1, col2, col3 = st.columns(3)
        col1.metric("Success rate", summary.get("success_rate", "N/A"))
        col2.metric("Fastest (ms)", str(summary.get("fastest_ms", "N/A")))
        cheapest = summary.get("cheapest_cost_usd", 0.0)
        col3.metric("Cheapest ($)", f"{cheapest:.5f}" if isinstance(cheapest, float) else "N/A")
        if summary.get("fastest_model"):
            st.caption(f"Fastest model: {summary['fastest_model']}")
        if summary.get("cheapest_model"):
            st.caption(f"Cheapest model: {summary['cheapest_model']}")

    st.markdown("### Per-model results")
    for result in report.model_results:
        status = result.get("status", "unknown")
        header = (
            f"{result.get('provider', '?')} / {result.get('model_name', '?')} "
            f"[{result.get('stage', '?')}] - {status}"
        )
        with st.expander(header, expanded=(status != "success")):
            col1, col2, col3 = st.columns(3)
            col1.metric("Latency (ms)", result.get("latency_ms", 0))
            col2.metric("Est. cost ($)", f"{result.get('estimated_cost', 0.0):.5f}")
            quality = result.get("quality_notes", "")
            col3.metric("Quality", quality[:50] if quality else "-")
            preview = result.get("output_preview", "")
            if preview:
                st.text_area("Output preview", preview, height=100, disabled=True)
            error = result.get("error_message", "")
            if error:
                st.error(error)

    if report.observations:
        with st.expander("Full observations"):
            st.text(report.observations)


def main() -> None:
    _sidebar()
    tab1, tab2, tab3 = st.tabs(["Upload & Process", "Ask / Search", "Compare Models"])
    with tab1:
        _tab_upload()
    with tab2:
        _tab_ask()
    with tab3:
        _tab_compare()


main()
