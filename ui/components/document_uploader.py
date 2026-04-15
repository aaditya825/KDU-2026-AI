"""Document ingestion input components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import streamlit as st
except ImportError:  # pragma: no cover - import guard for scaffold validation.
    st = None


@dataclass(slots=True)
class IngestionRequest:
    source_type: str
    source: str | None = None
    uploaded_file: Any | None = None


def render_document_inputs() -> IngestionRequest | None:
    if st is None:
        return None
    with st.sidebar:
        st.subheader("Sources")

        pdf_submission: IngestionRequest | None = None
        with st.form("pdf-upload-form", clear_on_submit=False):
            uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
            submit_pdf = st.form_submit_button("Ingest PDF")
            if submit_pdf:
                if uploaded_file is None:
                    st.warning("Choose a PDF file before submitting.")
                else:
                    pdf_submission = IngestionRequest(
                        source_type="pdf",
                        source=uploaded_file.name,
                        uploaded_file=uploaded_file,
                    )

        url_submission: IngestionRequest | None = None
        with st.form("url-upload-form", clear_on_submit=False):
            url = st.text_input("Or submit a blog URL")
            submit_url = st.form_submit_button("Ingest URL")
            if submit_url:
                if not url.strip():
                    st.warning("Enter a blog URL before submitting.")
                else:
                    url_submission = IngestionRequest(source_type="url", source=url.strip())

        return pdf_submission or url_submission


def render_active_sources(sources: list[str]) -> None:
    if st is None or not sources:
        return
    with st.sidebar:
        st.caption("Active sources")
        for source in sources:
            st.write(f"- {source}")
