# Content Accessibility Suite Handoff Summary

## Current Status

Phases 1-3 are implemented and verified through CLI. Phase 4 Streamlit UI is implemented as a thin layer over the same backend controllers. Report/export generation under `reports/` is still pending.

The system currently supports:

- ingesting one file per command
- processing one file per command
- querying across all processed documents by default
- optional query/search scoping with `--file-id`
- grounded answers with supporting chunks shown in CLI output
- model comparison for one processed file
- Streamlit upload/process, ask/search, and model comparison tabs

Run verification:

```powershell
python -m pytest -q -p no:cacheprovider
```

Last known result: `11 passed`.

---

## Core User Flow

```powershell
python -m app.cli ingest <file_path>
python -m app.cli process <file_id>
python -m app.cli query "What are the key requirements?"
streamlit run app/streamlit_app.py
```

Optional scoped query:

```powershell
python -m app.cli query "What are the key requirements?" --file-id <file_id>
```

Search without answer generation:

```powershell
python -m app.cli search "requirements"
```

Model comparison:

```powershell
python -m app.cli compare <file_id>
```

---

## Implemented Architecture

| Area | Implementation |
|---|---|
| CLI | `app/cli.py` |
| Streamlit UI | `app/streamlit_app.py` |
| Config | `app/config/settings.py`, `app/config/model_registry.py` |
| File detection | `app/services/file_type_detector.py` |
| Validation | `app/services/file_validator.py` |
| Storage | `app/storage/file_storage.py` |
| Metadata DB | `app/repositories/file_repository.py` |
| Processing DB | `app/repositories/processing_repository.py` |
| Controllers | `app/controllers/` |
| Pipelines | `app/pipelines/` |
| Adapters | `app/adapters/` |
| Shared services | `app/services/` |
| Tests | `tests/unit/`, `tests/integration/` |

---

## Important Decisions

1. File routing is content-based.
   MIME type is detected from file bytes via `python-magic` in `file_type_detector.py`. Filename extension is fallback only when content detection cannot run.

2. Ingestion/processing are one file at a time.
   Each `ingest` command creates one `FileMetadata` row. Each `process` command processes one `file_id`.

3. Querying is cross-document by default.
   `query`, `ask`, and `search` do not require `file_id`. They search all queryable processed files. `--file-id` restricts to one file.

4. Answers are grounded.
   `AnswerService` receives retrieved chunks and prompts the LLM only with that context. CLI prints the answer plus supporting chunks, source file, page metadata, score, and confidence.

5. Retrieval has fallback behavior.
   Primary retrieval uses Sentence Transformers plus Chroma. If embeddings/vector search fail, the app falls back to keyword search over stored chunks.

6. Models are centralized.
   Model IDs and generation token budgets live in `app/config/model_registry.py`. Runtime code should not hardcode provider model IDs.

7. Supported cloud providers are Gemini and OpenAI only.
   Groq and OpenRouter were removed intentionally.

8. Default small model stack:
   Gemini `gemini-2.5-flash-lite` is default. OpenAI `gpt-5-mini` is optional fallback. Local fallback is used when cloud providers are unavailable.

9. Gemini SDK:
   Use `google-genai`, not deprecated `google-generativeai`.

10. Low-confidence extraction is preserved.
   Warnings/confidence/page metadata are stored and very-low-confidence chunks are filtered unless explicitly marked uncertain.

11. Model/input limits are enforced centrally.
   Upload size, PDF page count, image pixel count, audio duration, query length, retrieval `top_k`, LLM context caps, and embedding chunk sizes are declared through `settings.py` / `model_registry.py` and validated before expensive processing where possible.

12. Streamlit is thin UI only.
   Upload/process, ask/search, and comparison tabs call the existing controllers. Business logic should stay in services/controllers.

13. Runtime artifacts are ignored.
   Uploaded files, processed data, SQLite DBs, Chroma vectors, pytest temp files, report outputs, and Claude worktrees are not source artifacts.

---

## Supported Files

| Type | MIME examples | Pipeline |
|---|---|---|
| PDF | `application/pdf` | PDF direct text, OCR fallback, optional Gemini vision |
| Image | `image/jpeg`, `image/png`, `image/jpg` | OCR, optional Gemini vision |
| Audio | `audio/mpeg`, `audio/mp3`, `audio/wav`, `audio/x-wav`, `audio/wave` | `faster-whisper`, optional `whisper` fallback |

---

## Model Registry

File: `app/config/model_registry.py`

Current defaults:

```python
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_LLM_PROVIDER = "gemini"
LLM_PROVIDER_MODELS = {
    "gemini": "gemini-2.5-flash-lite",
    "openai": "gpt-5-mini",
    "local": "fallback",
}
VISION_PROVIDER_MODELS = {
    "gemini": "gemini-2.5-flash-lite",
}
DEFAULT_AUDIO_MODEL = "faster_whisper"
AUDIO_PROVIDER_MODELS = {
    "faster_whisper": "base",
    "whisper": "base",
}
LLM_FALLBACK_ORDER = ["gemini", "openai"]
```

Generation budgets:

```python
GENERATION_MAX_TOKENS = {
    "summary": 512,
    "key_points": 512,
    "topic_tags": 256,
    "answer": 1024,
    "comparison": 512,
}
```

Input/context guardrails:

```python
LLM_INPUT_TOKEN_LIMITS = {
    "gemini": 1_048_576,
    "openai": 400_000,
    "local": 8_000,
}
EMBEDDING_INPUT_TOKEN_LIMITS = {
    "all-MiniLM-L6-v2": 256,
}
DEFAULT_MAX_PDF_PAGES = 200
DEFAULT_MAX_IMAGE_PIXELS = 40_000_000
DEFAULT_MAX_QUERY_CHARS = 1_000
DEFAULT_MAX_RETRIEVAL_TOP_K = 20
DEFAULT_LLM_POSTPROCESS_INPUT_CHARS = 6_000
DEFAULT_QA_CONTEXT_CHARS = 12_000
DEFAULT_EMBEDDING_CHUNK_SIZE_CHARS = 1_000
DEFAULT_EMBEDDING_CHUNK_OVERLAP_CHARS = 200
```

---

## Environment

Use `.env.example` as template.

Important keys:

```text
GEMINI_API_KEY=
OPENAI_API_KEY=
DEFAULT_LLM_PROVIDER=gemini
DEFAULT_LLM_MODEL=gemini-2.5-flash-lite
DEFAULT_EMBEDDING_MODEL=all-MiniLM-L6-v2
DEFAULT_VECTOR_STORE=chroma
DEFAULT_AUDIO_MODEL=faster_whisper
MAX_UPLOAD_MB=25
MAX_AUDIO_DURATION_SEC=600
MAX_PDF_PAGES=200
MAX_IMAGE_PIXELS=40000000
MAX_QUERY_CHARS=1000
MAX_RETRIEVAL_TOP_K=20
```

No `GROQ_API_KEY` or `OPENROUTER_API_KEY` should be added back.

---

## Data Persistence

SQLite DB path:

```text
data/sqlite/cas.db
```

Main tables:

- `files`
- `processed_outputs`
- `chunks`
- `model_metrics`

Processed outputs persist:

- raw text
- cleaned text
- summary
- key points
- topic tags
- extraction method
- confidence
- page metadata
- warnings
- latency
- errors

Chunks persist:

- chunk text
- chunk index
- confidence
- source metadata
- vector reference if available

---

## Tests

Run:

```powershell
python -m pytest -q -p no:cacheprovider
```

Coverage currently includes:

- MIME-based file type routing
- unsupported content rejection
- processing persistence fields
- chunk page metadata
- retrieval re-index fallback
- comparison stages
- end-to-end backend flow

---

## Known Caveats

- `python-magic` may require system libmagic on Windows. If content detection cannot run, the detector falls back to filename-based MIME guessing.
- Sentence Transformers may download `all-MiniLM-L6-v2` on first use if not cached.
- If embeddings or Chroma fail, keyword retrieval keeps queries usable but with lower semantic quality.
- Audio transcription may require `ffmpeg` depending on the installed Whisper/faster-whisper stack.
- Streamlit UI is implemented, but report/export generation is still pending.
- The repositories still use naive UTC timestamps and produce Python deprecation warnings under Python 3.13.

---

## Phase 4 Current State

Streamlit entry point:

```powershell
streamlit run app/streamlit_app.py
```

Implemented tabs:

- Upload & Process
- Ask / Search
- Compare Models

The UI calls these existing controllers:

- `FileController.ingest_file`
- `ProcessingController.process_file`
- `SearchController.search`
- `SearchController.answer`
- `ComparisonController.compare`

Expected UI behavior:

- upload/process one file at a time
- show processed document status/list
- query all processed documents by default
- optionally filter to one selected file
- show answer and supporting chunks
- run model comparison for selected file
- generate reports under `reports/` when report/export work is added

Before starting UI work, rerun:

```powershell
python -m pytest -q -p no:cacheprovider
python -m app.cli --help
```

---

## Do Not Reintroduce

- Groq
- OpenRouter
- `google-generativeai`
- hardcoded provider model IDs in runtime modules
- extension-first file routing
- mandatory `file_id` for user query commands
