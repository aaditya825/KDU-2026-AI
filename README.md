# Content Accessibility Suite

Local-first multimodal accessibility app for PDFs, images, and audio. The app ingests one document at a time, processes it into searchable text/chunks, then answers user queries across all processed documents with supporting evidence.

## Current Status

- Phases 1-3 backend and CLI flow are implemented.
- Phase 4 Streamlit UI is implemented for upload/process, ask/search, and model comparison.
- Report/export generation under `reports/` is still pending.
- Guardrails are implemented for corrupt/locked files, missing dependencies, DB/vector/model failures, oversized inputs, meaningless queries, and low-confidence evidence.

## Supported Inputs

| Type | Supported formats | Pipeline |
|---|---|---|
| PDF | PDF | PyMuPDF text extraction, OCR fallback, optional Gemini vision fallback |
| Image | JPEG, PNG | Tesseract OCR, optional Gemini vision fallback |
| Audio | MP3, WAV | `faster-whisper` local transcription, optional `whisper` fallback |

File routing is based on detected MIME/content. Filename extension is fallback only.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill `.env` with keys only if cloud LLMs are needed:

```text
GEMINI_API_KEY=
OPENAI_API_KEY=
```

Gemini is the default cloud provider. OpenAI is optional fallback. Groq and OpenRouter are not supported.

## CLI Flow

```powershell
python -m app.cli ingest sample_doc.pdf
python -m app.cli process <file_id>
python -m app.cli query "What are the key requirements?"
```

Useful commands:

```powershell
python -m app.cli search "requirements"
python -m app.cli query "What are the key requirements?" --file-id <file_id>
python -m app.cli compare <file_id>
```

By default, `query`, `ask`, and `search` operate across all processed documents. `--file-id` is only for explicit scoping.

## Streamlit UI

```powershell
streamlit run app/streamlit_app.py
```

Current tabs:

- Upload & Process
- Ask / Search
- Compare Models

## Verification

```powershell
python -m pytest -q -p no:cacheprovider
python -m app.cli --help
```

Last verified result: `17 passed`.

## Runtime Data

Generated data is intentionally ignored by Git:

- `data/uploads/`
- `data/processed/`
- `data/sqlite/`
- `data/vector_db/`
- `tests/.tmp/`
- `pytest-cache-files-*/`
- `reports/`
- `.claude/worktrees/`

`.gitkeep` files preserve the expected folder structure.

## Main Docs

- `Docs/handoff_summary.md`
- `Docs/content_accessibility_suite_implementation_plan.md`
- `Docs/content_accessibility_suite_low_level_design.md`
- `Docs/architecture_decision_comparison.md`
- `Docs/claude_code_usage_guide.md`
