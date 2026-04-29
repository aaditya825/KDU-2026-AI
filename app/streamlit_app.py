"""
app/streamlit_app.py
─────────────────────
Phase 4 Streamlit UI for the Content Accessibility Suite.

Thin layer over existing controllers — no business logic here.

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

settings.configure_logging()

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Content Accessibility Suite",
    page_icon="📄",
    layout="wide",
)

_SUPPORTED_EXTENSIONS = ["pdf", "jpg", "jpeg", "png", "mp3", "wav"]
_SUPPORTED_LABEL = "PDF, JPEG, PNG, MP3, WAV"


# ── cached controllers (expensive to initialise) ───────────────────────────────
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


# ── lightweight repo helpers (fresh per call to avoid SQLite threading issues) ─
def _file_repo():
    from app.repositories.file_repository import FileRepository
    return FileRepository()


def _proc_repo():
    from app.repositories.processing_repository import ProcessingRepository
    return ProcessingRepository()


# ── display helpers ────────────────────────────────────────────────────────────
def _conf_color(conf: float) -> str:
    if conf >= 0.7:
        return "green"
    if conf >= 0.4:
        return "orange"
    return "red"


def _render_search_result(result, index: int) -> None:
    """Render one SearchResult as an expander."""
    conf = result.confidence
    source = result.file_name or result.source_metadata.get("file_name", "unknown")
    pages = result.source_metadata.get("pages") or result.source_metadata.get("page")
    score_label = f"score {result.score:.3f}"
    conf_label = f"conf {conf:.0%}"
    page_label = f"p.{pages}" if pages else ""
    header_parts = [f"[{index}]", source, score_label, conf_label]
    if page_label:
        header_parts.append(page_label)
    header = "  ·  ".join(header_parts)

    with st.expander(header, expanded=(index == 1)):
        if pages:
            st.caption(f"Source pages: {pages}")
        st.text(result.chunk_text[:700])


def _list_all_files():
    """Return (all_files, queryable_ids_set)."""
    try:
        all_files = _file_repo().list_all()
        queryable_ids = set(_proc_repo().list_queryable_file_ids())
        return all_files, queryable_ids
    except Exception as exc:
        st.error(f"Could not load document list: {exc}")
        return [], set()


# ── sidebar ────────────────────────────────────────────────────────────────────
def _sidebar() -> None:
    with st.sidebar:
        st.title("Content Accessibility Suite")
        st.caption("Upload → Process → Ask")
        st.divider()

        all_files, queryable_ids = _list_all_files()

        st.subheader("Documents")
        if not all_files:
            st.info("No documents uploaded yet.")
        else:
            for f in all_files:
                ready = f.file_id in queryable_ids
                icon = "✅" if ready else "⏳"
                label = "ready" if ready else f.status.value
                st.markdown(
                    f"{icon} **{f.original_name}**  \n"
                    f"<small style='color:grey'>{f.file_type.value} · {label}</small>",
                    unsafe_allow_html=True,
                )

        st.divider()
        st.caption(f"LLM: {settings.default_llm_provider} / {settings.default_llm_model}")
        gemini_ok = bool(settings.gemini_api_key)
        openai_ok = bool(settings.openai_api_key)
        st.caption(
            f"Gemini key: {'✅' if gemini_ok else '❌'}  "
            f"OpenAI key: {'✅' if openai_ok else '❌'}"
        )
        if not gemini_ok and not openai_ok:
            st.warning("No cloud API keys set. Local fallback will be used.", icon="⚠️")


# ── tab: Upload & Process ──────────────────────────────────────────────────────
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

    st.write(f"**{uploaded.name}** — {uploaded.size:,} bytes")

    if uploaded.size > settings.max_upload_bytes:
        st.error(
            f"File is too large ({uploaded.size / (1024 * 1024):.1f} MB). "
            f"Maximum allowed: {settings.max_upload_mb} MB."
        )
        return
    if not st.button("Ingest & Process", type="primary"):
        return

    # Save to a temp directory preserving the original filename
    # so FileController.ingest_file picks up the right original_name.
    tmpdir = tempfile.mkdtemp()
    tmp_path = Path(tmpdir) / uploaded.name
    try:
        tmp_path.write_bytes(uploaded.getbuffer())

        # ── ingest ────────────────────────────────────────────────────────
        file_meta = None
        try:
            with st.spinner("Ingesting file…"):
                file_meta = _file_controller().ingest_file(str(tmp_path))
        except Exception as exc:
            st.error(f"Ingestion failed: {exc}")
            return

        st.success(
            f"Ingested **{file_meta.original_name}** · "
            f"ID `{file_meta.file_id}` · "
            f"type {file_meta.file_type.value} · MIME {file_meta.mime_type}"
        )

        # ── process ───────────────────────────────────────────────────────
        try:
            with st.spinner("Extracting, summarising, embedding…"):
                result = _processing_controller().process_file(file_meta.file_id)
        except ValueError as exc:
            st.error(str(exc))
            return
        except Exception as exc:
            st.error(f"Processing failed: {exc}")
            return

        conf = result.extraction.confidence if result.extraction else 0.0
        method = result.extraction.method.value if result.extraction else "unknown"

        st.success(f"Processing complete — {result.latency_ms} ms")

        col1, col2, col3 = st.columns(3)
        col1.metric("Extraction method", method)
        col2.metric("Confidence", f"{conf:.0%}")
        col3.metric("Latency", f"{result.latency_ms} ms")

        if result.extraction and result.extraction.warnings:
            for w in result.extraction.warnings:
                st.warning(w)

        with st.expander("Extracted text preview"):
            st.text(result.cleaned_text[:1200] if result.cleaned_text else "(no text)")

        with st.expander("Summary"):
            st.write(result.summary or "(no summary)")

        with st.expander("Key points"):
            for pt in result.key_points:
                st.markdown(f"- {pt}")

        with st.expander("Topic tags"):
            st.write(", ".join(result.topic_tags) if result.topic_tags else "(none)")

        st.info("Document is now queryable. Switch to the **Ask / Search** tab.")
        st.rerun()

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ── tab: Ask / Search ─────────────────────────────────────────────────────────
def _tab_ask() -> None:
    st.header("Ask / Search")

    all_files, queryable_ids = _list_all_files()
    queryable_files = [f for f in all_files if f.file_id in queryable_ids]

    if not queryable_files:
        st.warning(
            "No processed documents found. "
            "Upload and process a document in the **Upload & Process** tab first."
        )
        return

    scope_labels = ["All documents"] + [f.original_name for f in queryable_files]
    scope_choice = st.selectbox("Search scope", scope_labels, index=0)

    selected_file_id: str | None = None
    if scope_choice != "All documents":
        selected = next(f for f in queryable_files if f.original_name == scope_choice)
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

    sc = _search_controller()
    scope_desc = f"file '{scope_choice}'" if selected_file_id else "all documents"

    if mode == "Q&A":
        with st.spinner(f"Answering from {scope_desc}…"):
            try:
                answer_result = sc.answer(
                    file_id=selected_file_id,
                    question=question,
                    top_k=int(top_k),
                )
            except ValueError as exc:
                st.error(str(exc))
                return
            except Exception as exc:
                st.error(f"Q&A failed: {exc}")
                return

        if answer_result.insufficient_evidence:
            st.warning(
                "Insufficient evidence in the processed documents to answer this question. "
                "The answer below may be incomplete.",
                icon="⚠️",
            )
        else:
            st.success("Answer generated from retrieved context.")

        st.markdown("### Answer")
        st.markdown(answer_result.answer)

        if answer_result.confidence_notes:
            st.caption(f"Note: {answer_result.confidence_notes}")

        st.markdown("### Supporting chunks")
        if answer_result.supporting_chunks:
            for i, chunk in enumerate(answer_result.supporting_chunks, 1):
                _render_search_result(chunk, i)
        else:
            st.info("No supporting chunks returned.")

    else:
        with st.spinner(f"Searching {scope_desc}…"):
            try:
                results = sc.search(
                    file_id=selected_file_id,
                    query=question,
                    top_k=int(top_k),
                )
            except ValueError as exc:
                st.error(str(exc))
                return
            except Exception as exc:
                st.error(f"Search failed: {exc}")
                return

        if not results:
            st.info("No relevant chunks found for that query.")
            return

        st.success(f"{len(results)} chunk(s) found")
        for i, r in enumerate(results, 1):
            _render_search_result(r, i)


# ── tab: Compare Models ────────────────────────────────────────────────────────
def _tab_compare() -> None:
    st.header("Model Comparison")
    st.write(
        "Runs summary, key-points, and topic-tag stages across all configured LLM providers "
        "for a selected document and records latency, estimated cost, and quality notes."
    )

    all_files, queryable_ids = _list_all_files()
    queryable_files = [f for f in all_files if f.file_id in queryable_ids]

    if not queryable_files:
        st.warning(
            "No processed documents found. "
            "Upload and process a document in the **Upload & Process** tab first."
        )
        return

    file_names = [f.original_name for f in queryable_files]
    choice = st.selectbox("Select document", file_names)
    selected = next(f for f in queryable_files if f.original_name == choice)

    if not st.button("Run Comparison", type="primary"):
        return

    from app.controllers.comparison_controller import ComparisonController

    cc = ComparisonController()
    with st.spinner(f"Running comparison for {selected.original_name}…"):
        try:
            report = cc.compare(selected.file_id)
        except ValueError as exc:
            st.error(str(exc))
            return
        except Exception as exc:
            st.error(f"Comparison failed: {exc}")
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
    for r in report.model_results:
        status = r.get("status", "unknown")
        header = (
            f"{r.get('provider', '?')} / {r.get('model_name', '?')} "
            f"[{r.get('stage', '?')}] — {status}"
        )
        with st.expander(header, expanded=(status != "success")):
            col1, col2, col3 = st.columns(3)
            col1.metric("Latency (ms)", r.get("latency_ms", 0))
            col2.metric("Est. cost ($)", f"{r.get('estimated_cost', 0.0):.5f}")
            quality = r.get("quality_notes", "")
            col3.metric("Quality", quality[:50] if quality else "—")
            preview = r.get("output_preview", "")
            if preview:
                st.text_area("Output preview", preview, height=100, disabled=True)
            err = r.get("error_message", "")
            if err:
                st.error(err)

    if report.observations:
        with st.expander("Full observations"):
            st.text(report.observations)


# ── entry point ────────────────────────────────────────────────────────────────
def main() -> None:
    _sidebar()
    tab1, tab2, tab3 = st.tabs(["📤 Upload & Process", "💬 Ask / Search", "📊 Compare Models"])
    with tab1:
        _tab_upload()
    with tab2:
        _tab_ask()
    with tab3:
        _tab_compare()


main()

