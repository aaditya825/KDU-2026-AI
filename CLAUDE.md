# CLAUDE.md

## Project Context

- This repository implements the Content Accessibility Suite assignment.
- Read `Docs/handoff_summary.md`, `Docs/content_accessibility_suite_low_level_design.md`, `Docs/content_accessibility_suite_implementation_plan.md`, and `Docs/architecture_decision_comparison.md` before architecture-level changes.
- The implementation is backend-first. CLI behavior is the source of truth for backend behavior, and Streamlit is a thin UI over the same controllers.
- Ingestion and processing happen one file at a time.
- Querying is cross-document by default after documents have been processed.
- `query`, `ask`, and `search` accept optional `--file-id` only when a caller wants to restrict the operation to one document.
- File routing is content-based. Use MIME detection through `app/services/file_type_detector.py`; do not add extension-first routing.
- Model names and generation limits live in `app/config/model_registry.py`; do not hardcode provider model IDs in adapters/services.
- Supported cloud providers are Gemini and OpenAI only. Groq and OpenRouter are intentionally removed.
- Default small model is Gemini `gemini-2.5-flash-lite`; optional OpenAI fallback is `gpt-5-mini`.
- Gemini integration uses `google-genai`, not deprecated `google-generativeai`.
- Default retrieval uses Sentence Transformers plus Chroma, with keyword fallback if embeddings/vector search fail.
- Grounded Q&A must return answers from retrieved chunks and show supporting chunks.

## Workflow Rules

- Keep changes small and verifiable.
- Prefer CLI verification during phases 1-3.
- Keep Streamlit as a thin layer over the working controllers.
- Preserve low-confidence extraction metadata. Do not silently treat uncertain extraction as reliable evidence.
- If retrieval or model providers fail, preserve useful degraded behavior through fallback paths.
- Do not reintroduce Groq, OpenRouter, or extension-first routing.

## Useful Commands

- Inspect repository: `Get-ChildItem -Force`
- Search files: `rg "<term>"`
- Run help: `python -m app.cli --help`
- Run tests: `python -m pytest -q -p no:cacheprovider`
- Ingest: `python -m app.cli ingest <file_path>`
- Process: `python -m app.cli process <file_id>`
- Query all processed documents: `python -m app.cli query "question"`
- Query one document: `python -m app.cli query "question" --file-id <file_id>`
- Search all processed documents: `python -m app.cli search "query text"`
- Compare models for one file: `python -m app.cli compare <file_id>`
- Phase 4 UI: `streamlit run app/streamlit_app.py`

## Current Implemented Decisions

- MIME/content detection is implemented in `file_type_detector.py`.
- SQLite stores files, processed outputs, chunks, and metrics.
- Chroma stores vectors, but query falls back to keyword search when needed.
- `query` and `ask` search all queryable processed documents by default.
- CLI answer output includes supporting chunks, score, confidence, file, and pages.
- Model registry owns Gemini/OpenAI model IDs and token budgets.
- Tests cover the main backend flow and critical fallback behavior.
- Streamlit upload/process, ask/search, and model comparison tabs are implemented.
- Report/export generation under `reports/` is still pending.
