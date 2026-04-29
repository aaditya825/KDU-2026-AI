# Content Accessibility Suite Implementation Plan

## Summary

The Content Accessibility Suite is implemented backend-first. The CLI exposes the core behavior, and Phase 4 adds Streamlit as a thin UI layer over the same controllers and services.

Implemented flow:

1. Ingest one document at a time.
2. Detect file type from MIME/content, not extension-first.
3. Process each ingested document into cleaned text, summary, key points, tags, metadata, and chunks.
4. Query across all processed documents by default.
5. Return an answer grounded in retrieved chunks, with the supporting chunks shown in CLI output.

Current default stack:

- Local file storage under `data/uploads/`
- SQLite metadata under `data/sqlite/cas.db`
- Content-based MIME detection through `python-magic` when available
- Sentence Transformers `all-MiniLM-L6-v2` for local embeddings
- Chroma as the default vector database
- `faster-whisper` for audio transcription, with `whisper` as fallback
- Direct PDF text extraction first, then OCR, then optional Gemini vision fallback
- Gemini `gemini-2.5-flash-lite` as the default small cloud LLM/vision model
- OpenAI `gpt-5-mini` as optional small fallback
- Local fallback adapter when cloud credentials/packages are unavailable

Groq and OpenRouter are intentionally not supported in the current implementation.

---

## Implemented Decisions

| Area | Decision |
|---|---|
| File intake | CLI accepts one file per ingest command. Multiple files are represented as multiple ingested records. |
| Type routing | Routing uses detected MIME type from file content via `app/services/file_type_detector.py`. Extension is fallback only when content detection cannot run. |
| Supported file types | PDF, JPEG, PNG, MP3, WAV. |
| Storage | Files are copied to a controlled uploads directory with UUID file IDs and sanitized names. |
| Metadata | File records, processed outputs, chunks, and model metrics are stored in SQLite. |
| Processing | PDF, image, and audio use separate pipelines behind `ContentRouter`. |
| PDF extraction | PyMuPDF direct extraction first; OCR/vision fallback for low-text pages; page markers are preserved for retrieval metadata. |
| Image extraction | Tesseract OCR first; optional Gemini vision fallback. |
| Audio extraction | `faster-whisper` default; `whisper` fallback. |
| Models | Model IDs are centralized in `app/config/model_registry.py`; runtime code must not hardcode provider model names. |
| Input limits | File size, PDF pages, image pixels, audio duration, query length, retrieval `top_k`, LLM context caps, and embedding chunk sizes are centralized and enforced before expensive work where possible. |
| Cloud providers | Only Gemini and OpenAI are supported; Gemini is default. |
| Embeddings | Sentence Transformers local embeddings are default. If embedding/vector search fails, query falls back to keyword search over stored chunks. |
| Vector store | Chroma stores chunk vectors per file. Missing/partial vector collections trigger re-index from SQLite chunks. |
| Query scope | `query`, `ask`, and `search` run across all queryable processed documents by default. `--file-id` can restrict to one document. |
| Answer grounding | The LLM receives only retrieved chunks as context. Very-low-confidence chunks are excluded unless explicitly marked uncertain. |
| Answer output | CLI shows final answer plus exact supporting chunks, scores, confidence, source file, and source pages. |
| Model comparison | Comparison runs summary, key-points, and topic-tag stages across configured models and records latency/cost/quality notes. |
| Streamlit UI | `app/streamlit_app.py` uploads/processes one file, queries/searches processed documents, shows supporting chunks, and runs comparison. |
| Failure behavior | Cloud/model failures degrade to local fallback where possible. Empty or failed processed records are skipped in global query. |
| Tests | Unit and integration tests cover type detection, processing persistence, retrieval fallback, chunk metadata, comparison, and backend flow. |

---

## Phase 1: Backend Foundation and Single-File Ingestion

Status: implemented.

Implemented components:

- Backend package structure under `app/`
- `.env` configuration through `app/config/settings.py`
- Central model registry in `app/config/model_registry.py`
- Content-based file type detection in `app/services/file_type_detector.py`
- File validation in `app/services/file_validator.py`
- Local file storage in `app/storage/file_storage.py`
- SQLite file metadata persistence in `app/repositories/file_repository.py`
- CLI ingestion command:

```powershell
python -m app.cli ingest <file_path>
```

The ingest command returns:

- file ID
- original file name
- detected file type
- MIME type
- size
- stored path
- status

---

## Phase 2: Backend Extraction and Output Generation

Status: implemented.

Implemented components:

- Content router in `app/pipelines/content_router.py`
- PDF pipeline in `app/pipelines/pdf_pipeline.py`
- Image pipeline in `app/pipelines/image_pipeline.py`
- Audio pipeline in `app/pipelines/audio_pipeline.py`
- OCR/vision/audio/LLM adapter interfaces under `app/adapters/`
- Common post-processing in `app/services/post_processor.py`
- Text cleaning in `app/services/text_cleaner.py`
- Processing persistence in `app/repositories/processing_repository.py`

Stored processing fields:

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
- total processing latency
- errors

CLI processing command:

```powershell
python -m app.cli process <file_id>
```

---

## Phase 3: Search, Grounded Q&A, and Model Comparison

Status: implemented.

Implemented components:

- Chunking with overlap in `app/services/chunker.py`
- Local embedding adapter in `app/adapters/embedding_adapter.py`
- Chroma vector adapter in `app/adapters/vector_store_adapter.py`
- Search orchestration in `app/controllers/search_controller.py`
- Grounded answer generation in `app/services/answer_service.py`
- Comparison service in `app/services/comparison_service.py`
- Answer controller wrapper in `app/controllers/answer_controller.py`

Default query flow:

```powershell
python -m app.cli query "What are the key requirements?"
```

Equivalent command:

```powershell
python -m app.cli ask "What are the key requirements?"
```

Scoped query:

```powershell
python -m app.cli query "What are the key requirements?" --file-id <file_id>
```

Search-only command:

```powershell
python -m app.cli search "requirements"
```

Model comparison command:

```powershell
python -m app.cli compare <file_id>
```

Grounding rules:

- Query is embedded and matched against stored chunks when embedding/vector search is available.
- If semantic search is unavailable, keyword fallback retrieves relevant stored chunks.
- The LLM is prompted only with retrieved chunks.
- Insufficient evidence is returned when retrieved chunks do not support the answer.
- Supporting chunks are printed in CLI output.

---

## Phase 4: Streamlit UI, Reports, and Submission Polish

Status: partially implemented.

Implemented:

- Streamlit entry point: `app/streamlit_app.py`
- Upload and process one file at a time.
- Query all processed documents by default.
- Allow optional document filtering in the UI.
- Display answer plus supporting chunks and metadata.
- Run model comparison for a selected processed file.
- Keep UI as a thin layer over controllers.

Pending:

- Add report/export generation under `reports/`.
- Add final screenshots or sample outputs if required for submission.

Current UI screens:

- Upload and process
- Processed document list/status
- Query all documents
- Supporting chunks/evidence view
- Model comparison

---

## Public Interfaces

```python
class FileController:
    def ingest_file(self, path: str) -> FileMetadata:
        ...

class ProcessingController:
    def process_file(self, file_id: str) -> ProcessingResult:
        ...

class SearchController:
    def search(self, file_id: str | None, query: str, top_k: int) -> list[SearchResult]:
        ...

    def answer(self, file_id: str | None, question: str, top_k: int) -> AnswerResult:
        ...

class AnswerController:
    def answer(self, file_id: str | None, query: str, top_k: int) -> AnswerResult:
        ...

class ComparisonController:
    def compare(self, file_id: str) -> ComparisonReport:
        ...
```

---

## Test Plan

Automated tests:

```powershell
python -m pytest -q -p no:cacheprovider
```

CLI smoke tests:

```powershell
python -m app.cli ingest <file_path>
python -m app.cli process <file_id>
python -m app.cli query "What are the key requirements?"
python -m app.cli search "requirements"
python -m app.cli compare <file_id>
streamlit run app/streamlit_app.py
```

Important acceptance checks:

- A supported file with misleading extension is routed by MIME/content.
- Unsupported content is rejected even if extension appears valid.
- Query works without passing `file_id`.
- Query output includes supporting chunks.
- Semantic search falls back to keyword search when embedding/vector search is unavailable.
- Low-confidence chunks are surfaced and not silently treated as verified.

---

## Assumptions and Defaults

- Backend was implemented before Streamlit.
- CLI remains the primary verification mechanism for backend behavior.
- Streamlit reuses the same controllers rather than duplicating business logic.
- One file is ingested and processed per command.
- Querying is cross-document by default after processing.
- Chroma is the default vector DB.
- Sentence Transformers `all-MiniLM-L6-v2` is the default embedding model.
- Gemini `gemini-2.5-flash-lite` is the default cloud LLM/vision model.
- OpenAI `gpt-5-mini` is optional fallback.
- Groq and OpenRouter are excluded.
- Cloud providers are optional and configured through `.env`.
- Low-confidence extraction is never silently treated as reliable evidence.
- Runtime/generated folders are ignored: uploaded files, processed data, SQLite DBs, Chroma vectors, pytest temp files, and report outputs.
