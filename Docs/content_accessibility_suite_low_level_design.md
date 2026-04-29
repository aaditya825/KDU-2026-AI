# Low-Level Design: Content Accessibility Suite

## 1. Overview

The Content Accessibility Suite processes PDFs, images, and audio into accessible text outputs, stores searchable chunks, and answers user questions using retrieved evidence. The backend is exposed through CLI commands, and Streamlit is implemented as a thin UI over the same backend.

Current user flow:

1. User ingests one document.
2. App detects the content type from MIME/file bytes.
3. User processes the document.
4. User can query across all processed documents.
5. App returns a grounded answer plus supporting chunks.

---

## 2. Implemented Architecture

| Layer | Responsibility |
|---|---|
| CLI | User-facing commands for ingest, process, query, search, and compare. |
| Streamlit UI | Upload/process, ask/search, and comparison screens over the same controllers. |
| Controllers | Coordinate file, processing, search, answer, and comparison flows. |
| Pipelines | Modality-specific extraction for PDF, image, and audio. |
| Services | Validation, content type detection, cleaning, chunking, answer generation, search, comparison. |
| Adapters | Replaceable providers for OCR/vision, audio, LLM, embeddings, and vector store. |
| Repositories | SQLite persistence for files, processed outputs, chunks, and metrics. |
| Storage | Local file copy and path management. |
| Config | Settings and centralized model registry. |

---

## 3. Implemented Decisions

| Decision | Implementation |
|---|---|
| Content-based routing | `app/services/file_type_detector.py` detects MIME via `python-magic`; extension is fallback only. |
| One-file ingestion | `FileController.ingest_file()` accepts one path and stores one file record. |
| Cross-document query | `SearchController.search(None, query)` and `answer(None, question)` search all queryable processed files. |
| Optional scoping | `--file-id` restricts query/search to one processed file. |
| Central model declarations | `app/config/model_registry.py` owns provider model IDs and generation token limits. |
| Provider policy | Supported cloud providers are Gemini and OpenAI only. Groq and OpenRouter are removed. |
| Small model defaults | Gemini `gemini-2.5-flash-lite` is default; OpenAI `gpt-5-mini` is optional fallback. |
| Current Gemini SDK | Gemini calls use `google-genai`, not deprecated `google-generativeai`. |
| Input guardrails | File size, PDF pages, image pixels, audio duration, query length, and retrieval `top_k` are validated before expensive processing/querying. |
| Retrieval fallback | If embeddings/Chroma fail, keyword search over stored chunks is used. |
| Evidence display | CLI answer output shows supporting chunks, score, confidence, source file, and pages. |
| Duplicate control | Search/answer paths dedupe repeated chunk hits before display/model prompting. |
| Low-confidence handling | Very-low-confidence chunks are excluded unless marked uncertain. |
| Failure handling | Empty/failed processed records are skipped in global query. Cloud failures use local fallback. |
| Testing | Unit and integration tests cover detection, persistence, retrieval fallback, chunk metadata, comparison, and backend flow. |
| Runtime cleanup | Generated uploads, processed data, SQLite DBs, Chroma vectors, pytest temp files, and report outputs are ignored; `.gitkeep` placeholders preserve folder structure. |

---

## 4. File Intake and Routing

### Supported Content

| Content | MIME types | Pipeline |
|---|---|---|
| PDF | `application/pdf` | `PDFProcessingPipeline` |
| Image | `image/jpeg`, `image/png`, `image/jpg` | `ImageProcessingPipeline` |
| Audio | `audio/mpeg`, `audio/mp3`, `audio/wav`, `audio/x-wav`, `audio/wave` | `AudioProcessingPipeline` |

### Detection Flow

```text
source file
-> FileValidator
-> detect_mime_type(path)
-> resolve_file_type(mime)
-> FileStorage.save()
-> FileMetadata(file_type, mime_type)
-> ContentRouter.get_pipeline(file_type)
```

`python-magic` is preferred because it reads file bytes. `mimetypes` and extension mapping are fallback only when libmagic is unavailable.

---

## 5. Processing Pipelines

| Pipeline | Steps |
|---|---|
| PDF | PyMuPDF direct text extraction; render low-text pages; OCR fallback; optional Gemini vision fallback; add page markers. |
| Image | Tesseract OCR; optional Gemini vision fallback when OCR is low-confidence or empty. |
| Audio | `faster-whisper`; fallback to `whisper` if configured/available. |

Processing output persists:

- raw text
- cleaned text
- summary
- key points
- topic tags
- extraction method
- confidence
- page metadata
- warnings
- extraction latency
- total latency
- error message

---

## 6. Model and Provider Design

All model IDs live in `app/config/model_registry.py`.

```python
LLM_PROVIDER_MODELS = {
    "gemini": "gemini-2.5-flash-lite",
    "openai": "gpt-5-mini",
    "local": "fallback",
}

VISION_PROVIDER_MODELS = {
    "gemini": "gemini-2.5-flash-lite",
}

AUDIO_PROVIDER_MODELS = {
    "faster_whisper": "base",
    "whisper": "base",
}

LLM_FALLBACK_ORDER = ["gemini", "openai"]
```

Provider choices:

- Gemini is the default small cloud provider.
- OpenAI is an optional small fallback.
- Local fallback is used when no cloud provider is usable.
- Groq and OpenRouter are not part of the implementation.

Benchmark details and source links are maintained in `Docs/architecture_decision_comparison.md`.

### Model Selection Rationale

The selected stack is intentionally hybrid. Local models/tools are used where the workload is deterministic, privacy-sensitive, or high-volume. Small cloud models are used only where natural-language generation or multimodal reasoning adds value.

| Component | Selected model/tool | Rationale |
|---|---|---|
| PDF direct text | PyMuPDF | Extracts embedded PDF text locally without model cost, network dependency, or privacy exposure. |
| Scanned PDF OCR | Tesseract OCR | Mature local OCR option. Keeps scans local and avoids paying for every page. |
| Image OCR | Tesseract OCR | Good default for clean screenshots/scans. Cloud vision is optional only when OCR is insufficient. |
| Optional vision fallback | Gemini `gemini-2.5-flash-lite` | Provides multimodal understanding with a large context window and low cost when OCR cannot produce reliable text. |
| Audio transcription | `faster-whisper` `base` | Local CPU/int8 transcription keeps audio private and avoids cloud audio cost. `base` balances speed, size, and quality. |
| Audio fallback | `whisper` `base` | Keeps a compatible local fallback when faster-whisper is not available. |
| Embeddings | `all-MiniLM-L6-v2` | Small local embedding model, 384-dimensional vectors, no API cost, suitable for sentence/paragraph retrieval. Chunking keeps inputs below the practical 256 word-piece window. |
| Default LLM | Gemini `gemini-2.5-flash-lite` | Selected because it is the lowest-cost Gemini 2.5 option, supports multimodal input, and has a 1M-token context window. Suitable for high-volume summaries, tags, and grounded Q&A. |
| LLM fallback | OpenAI `gpt-5-mini` | Provides a second cloud provider with a large context window when Gemini is unavailable. It is not primary because it is more expensive for expected output-heavy workloads. |
| Last-resort fallback | Local rule-based adapter | Ensures CLI/UI degrade gracefully when cloud keys or SDKs are missing. |

Models not selected by default:

- Gemini `gemini-2.5-flash` is stronger but has materially higher output cost than Flash-Lite. It should only be promoted if quality evaluation shows Flash-Lite is insufficient.
- OpenAI `gpt-5-nano` is cheaper than `gpt-5-mini`, but it is better suited to summarization/classification than grounded Q&A. It can be reconsidered later for topic-tag or classification-only stages.
- Larger local Whisper models can improve transcription quality but increase CPU/RAM usage and latency. The app starts with `base` for predictable local execution.

Generation token limits are also centralized:

```python
GENERATION_MAX_TOKENS = {
    "summary": 512,
    "key_points": 512,
    "topic_tags": 256,
    "answer": 1024,
    "comparison": 512,
}
```

Input and context limits are centralized:

```python
LLM_INPUT_TOKEN_LIMITS = {
    "gemini": 1_048_576,
    "openai": 400_000,
    "local": 8_000,
}

LLM_OUTPUT_TOKEN_LIMITS = {
    "gemini": 65_536,
    "openai": 128_000,
    "local": 1_024,
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

Validation placement:

- `FileValidator` rejects oversized files, unsupported content, over-page PDFs, over-pixel images, and over-duration audio before storage/processing.
- `SearchController` rejects empty/overlong queries and invalid `top_k` before embedding/search.
- `PostProcessor` truncates extracted text before LLM summary/key-point/tag generation.
- `AnswerService` caps the retrieved context sent to the LLM.
- `chunker.py` keeps chunks below the embedding model's practical input window.

---

## 7. Search and Grounded Q&A

### Chunking

`app/services/chunker.py` splits cleaned text into overlapping chunks. Chunks preserve:

- file ID
- file name
- chunk index
- extraction confidence
- page numbers parsed from `[PAGE n]` markers
- page metadata
- extraction method

### Retrieval

Primary retrieval:

```text
query -> embed_query -> Chroma search -> SearchResult[]
```

Fallback retrieval:

```text
query -> tokenize -> keyword overlap over SQLite chunks -> SearchResult[]
```

Fallback is used when:

- embedding model cannot load
- Chroma search fails
- vector collection is missing and cannot be rebuilt

### Answer Generation

```text
question
-> retrieve chunks across all queryable files
-> dedupe chunks
-> filter very-low-confidence chunks
-> build grounded prompt
-> LLMAdapter.generate()
-> AnswerResult(answer, supporting_chunks, confidence_notes)
```

The LLM never receives the user question without retrieved context.

---

## 8. Database and Storage Design

Detailed database/storage comparison and source links are maintained in `Docs/architecture_decision_comparison.md`.

Current persistence stack:

```text
uploaded files -> local filesystem under data/uploads/
metadata / outputs / chunks / metrics -> SQLite under data/sqlite/cas.db
embeddings / vector similarity index -> Chroma under data/vector_db/
```

### Database Selection Rationale

| Storage need | Selected option | Rationale |
|---|---|---|
| Original files | Local filesystem | Keeps large binaries out of SQLite, is easy to inspect, and is sufficient for local-first Phase 1-4 usage. |
| File metadata/status | SQLite | Serverless, zero-configuration, transactional, Python-friendly, and enough for single-user/local workflows. |
| Processed outputs | SQLite | Summaries, key points, tags, warnings, confidence, and errors are structured relational records. |
| Chunks and source metadata | SQLite | Keeps chunk text as source of truth, enables keyword fallback, and allows Chroma re-indexing if vector data is missing. |
| Dense vector search | Chroma | Purpose-built for embeddings and similarity search with metadata; simpler than building vector search manually in SQLite. |
| Production future option | PostgreSQL + pgvector | Better for multi-user concurrency, managed backups, tenant isolation, and consolidating metadata/vector search. Not needed for the current local-first scope. |

### Why SQLite Was Chosen

SQLite is used because the app currently needs local durability without database server operations. It fits this project because:

- no separate DB server is required
- works from CLI and Streamlit with the same local file
- supports ACID transactions for file/process status updates
- keeps setup simple for development and evaluation
- stores tabular records more cleanly than JSON files

SQLite is not treated as the final answer for a high-concurrency hosted system. If the app becomes multi-user or production-hosted, migrate the relational tables to PostgreSQL.

### Why Chroma Was Chosen

Chroma is used only for vector search. SQLite remains the source of truth for chunks. This split is intentional:

- Chroma handles vector similarity search.
- SQLite stores chunk text and metadata for citations.
- If Chroma is missing or partial, vectors can be rebuilt from SQLite chunks.
- If Chroma fails, keyword fallback can search SQLite chunks.

### Why Not PostgreSQL Yet

PostgreSQL, especially with `pgvector`, is a strong production target, but it adds operational overhead now:

- DB server installation/configuration
- credentials and migrations
- more setup for local testing
- unnecessary complexity for current single-machine CLI/Streamlit flow

PostgreSQL should be introduced when the app needs concurrent users, tenant isolation, cloud deployment, managed backups, or stronger production operations.

---

## 9. CLI Design

### Ingest

```powershell
python -m app.cli ingest <file_path>
```

Returns file ID, MIME type, detected file type, stored path, status.

### Process

```powershell
python -m app.cli process <file_id>
```

Runs extraction and post-processing for one file.

### Query Across All Processed Files

```powershell
python -m app.cli query "What are the key requirements?"
```

`ask` is equivalent:

```powershell
python -m app.cli ask "What are the key requirements?"
```

### Query One File

```powershell
python -m app.cli query "What are the key requirements?" --file-id <file_id>
```

### Search Without Answer Generation

```powershell
python -m app.cli search "requirements"
```

### Compare Models

```powershell
python -m app.cli compare <file_id>
```

---

## 10. Streamlit UI Design

Entry point:

```powershell
streamlit run app/streamlit_app.py
```

The Streamlit app is intentionally thin. It imports the repository root into `sys.path` so `streamlit run app/streamlit_app.py` can resolve absolute imports such as `app.config.settings`.

Implemented tabs:

| Tab | Behavior |
|---|---|
| Upload & Process | Upload one file, enforce size limit before ingestion, call `FileController.ingest_file()`, then `ProcessingController.process_file()`. |
| Ask / Search | Query all processed documents by default; optionally scope to a selected processed document; display answer/search results with supporting chunks. |
| Compare Models | Run `ComparisonController.compare()` for a selected processed document and show latency/cost/quality metrics. |

The UI does not own business rules. File validation, processing, retrieval, answer generation, and model comparison remain in controllers/services.

Pending UI/report work:

- Export reports under `reports/`.
- Add final screenshots/sample outputs if required for submission.

---

## 11. Data Model

### `files`

| Column | Notes |
|---|---|
| `file_id` | UUID primary key |
| `original_name` | User-supplied filename |
| `stored_path` | Local storage path |
| `file_type` | `pdf`, `image`, `audio` |
| `mime_type` | Detected MIME type |
| `size_bytes` | Stored file size |
| `status` | `uploaded`, `processing`, `completed`, `failed` |
| `created_at`, `updated_at` | Timestamps |

### `processed_outputs`

| Column | Notes |
|---|---|
| `output_id` | UUID primary key |
| `file_id` | Linked file |
| `raw_text` | Extraction/transcription output |
| `cleaned_text` | Normalized text |
| `summary` | Generated summary |
| `key_points` | JSON list |
| `topic_tags` | JSON list |
| `extraction_method` | Direct text, OCR, vision, whisper, etc. |
| `confidence` | Extraction confidence |
| `page_metadata` | JSON page/region metadata |
| `latency_ms` | Total processing latency |
| `extraction_latency_ms` | Extraction stage latency |
| `warnings` | JSON warning list |
| `error_message` | Failure detail |
| `created_at` | Timestamp |

### `chunks`

| Column | Notes |
|---|---|
| `chunk_id` | UUID primary key |
| `file_id` | Linked file |
| `chunk_index` | Position in processed text |
| `text` | Chunk text |
| `confidence` | Carried extraction confidence |
| `metadata` | JSON source metadata |
| `vector_ref` | Optional vector reference |

### `model_metrics`

| Column | Notes |
|---|---|
| `metric_id` | UUID primary key |
| `file_id` | Linked file |
| `stage` | summary, key_points, topic_tags, etc. |
| `model_name` | Registry model ID |
| `provider` | gemini, openai, local |
| `latency_ms` | Stage latency |
| `estimated_cost` | Estimated cost |
| `status` | success/failed |
| `error_message` | Failure detail |

---

## 12. Configuration

`.env.example`:

```text
GEMINI_API_KEY=
OPENAI_API_KEY=

DATA_DIR=data
SQLITE_DB_PATH=data/sqlite/cas.db

MAX_UPLOAD_MB=25
MAX_AUDIO_DURATION_SEC=600
MAX_PDF_PAGES=200
MAX_IMAGE_PIXELS=40000000
MAX_QUERY_CHARS=1000
MAX_RETRIEVAL_TOP_K=20

DEFAULT_VECTOR_STORE=chroma
DEFAULT_EMBEDDING_MODEL=all-MiniLM-L6-v2
DEFAULT_LLM_PROVIDER=gemini
DEFAULT_LLM_MODEL=gemini-2.5-flash-lite
DEFAULT_VISION_PROVIDER=ocr
DEFAULT_AUDIO_MODEL=faster_whisper

LOCAL_ONLY=false
LOG_LEVEL=INFO
```

---

## 13. Reliability and Error Handling

| Failure | Handling |
|---|---|
| Unsupported content | Rejected by MIME type during validation. |
| Missing libmagic | Falls back to filename-based MIME guessing. |
| Empty extraction | File marked failed; persisted error detail. |
| LLM package/key missing | Uses local fallback adapter. |
| LLM API failure | Uses local fallback answer/message where possible. |
| Embedding/Chroma failure | Uses keyword fallback retrieval. |
| Missing vector collection | Re-indexes from SQLite chunks when possible. |
| Empty processed records | Skipped during global query. |
| Low-confidence extraction | Warning retained; uncertain chunks marked/filtered. |

---

## 14. Testing Strategy

Automated tests:

```powershell
python -m pytest -q -p no:cacheprovider
```

Current coverage includes:

- MIME-based file type routing
- unsupported content rejection
- processing persistence fields
- chunk page metadata
- retrieval re-index fallback
- model comparison stages
- backend flow from ingest to process to query

Manual acceptance:

```powershell
python -m app.cli ingest sample_doc.pdf
python -m app.cli process <file_id>
python -m app.cli query "What are the key requirements?"
python -m app.cli search "requirements"
python -m app.cli compare <file_id>
```

---

## 15. Remaining Work

- Add report/export generation under `reports/`.
- Add final screenshots or sample outputs if required for submission.
- Keep CLI and Streamlit behavior aligned whenever backend flow changes.
