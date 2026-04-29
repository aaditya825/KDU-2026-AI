# Architecture Decision Comparison: Models, Databases, and Storage

## Purpose

This document consolidates the comparison and selection rationale for:

- local and cloud AI models used by the Content Accessibility Suite
- database and storage choices used for files, metadata, chunks, metrics, and vectors

It separates:

- published provider/model/database facts
- published benchmark data where available
- measurements that must be collected manually in this application
- final selection rationale for the current Phase 1-4 implementation

Current implementation note:

- Phase 1-3 backend and CLI flows are implemented.
- Phase 4 Streamlit upload/process, ask/search, and model comparison screens are implemented.
- Report/export generation under `reports/` is pending.
- Groq and OpenRouter are intentionally excluded from the implemented provider set.

---

## 1. Model and AI Tool Decisions

### Current Application Model Stack

| Area | Current model/tool | Local/cloud | Current role |
|---|---|---|---|
| PDF direct text | PyMuPDF | Local | Extract embedded PDF text without LLM calls. |
| PDF OCR fallback | Tesseract OCR through `pytesseract` | Local | OCR scanned/low-text PDF pages. |
| Image OCR | Tesseract OCR through `pytesseract` | Local | Extract text from JPEG/PNG images. |
| Optional vision fallback | `gemini-2.5-flash-lite` | Cloud | Extract text/visual context when OCR is low-confidence and Gemini vision is enabled. |
| Audio transcription | `faster-whisper`, model size `base` | Local | Transcribe MP3/WAV audio. |
| Audio fallback | `whisper`, model size `base` | Local | Fallback if faster-whisper is not available/configured. |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | Local | Dense embeddings for semantic retrieval. |
| Vector store | Chroma | Local | Store/search chunk embeddings. |
| Default LLM | `gemini-2.5-flash-lite` | Cloud | Summary, key points, topic tags, grounded Q&A. |
| LLM fallback | `gpt-5-mini` | Cloud | Fallback if Gemini is unavailable. |
| Last-resort LLM | local rule-based fallback | Local | Avoid hard failure when cloud keys/packages are missing. |

Model IDs are declared in `app/config/model_registry.py`; runtime modules should not hardcode provider model names.

### Published Model Limits and Cost

| Model/tool | Input limit | Output limit | Published cost | Notes |
|---|---:|---:|---:|---|
| `gemini-2.5-flash-lite` | 1,048,576 tokens | 65,535 or 65,536 tokens, depending on Google API surface | $0.10 / 1M text/image/video input tokens, $0.30 / 1M audio input tokens, $0.40 / 1M output tokens | Multimodal input, text output. Selected as default cloud LLM. |
| `gemini-2.5-flash` | 1,048,576 tokens | 65,535 or 65,536 tokens | $0.30 / 1M text/image/video input tokens, $1.00 / 1M audio input tokens, $2.50 / 1M output tokens | Better capability candidate, higher cost. Not selected by default. |
| `gpt-5-mini` | 400,000 context window | 128,000 max output tokens | $0.25 / 1M input tokens, $2.00 / 1M output tokens | Selected OpenAI fallback. Text output; image input supported; audio/video not supported. |
| `gpt-5-nano` | 400,000 context window | 128,000 max output tokens | $0.05 / 1M input tokens, $0.40 / 1M output tokens | Cheaper OpenAI candidate for summarization/classification. Not selected because Q&A quality may be weaker. |
| `all-MiniLM-L6-v2` | Inputs longer than 256 word pieces are truncated by default | 384-dimensional embedding vector | No API cost when run locally | Good fit for short chunks and local retrieval. |
| Tesseract OCR | No token limit | Extracted text only | No API cost when run locally | Accuracy depends strongly on image quality. Tesseract docs recommend good quality and around 300 DPI. |
| `faster-whisper` | No token limit; constrained by audio duration, CPU/RAM | Transcript text | No API cost when run locally | Runtime depends on model size, hardware, audio length, and compute type. App uses `base`, CPU, int8. |

### Published Model Performance Data

#### faster-whisper

The official faster-whisper README reports benchmarks on a 13-minute audio file.

| Configuration from published benchmark | Hardware | Time | Memory |
|---|---|---:|---:|
| faster-whisper small, CPU, int8, beam size 5 | Intel Core i7-12700K, 8 threads | 1m42s | 1477 MB RAM |
| faster-whisper small, CPU, int8, batch size 8 | Intel Core i7-12700K, 8 threads | 51s | 3608 MB RAM |
| faster-whisper large-v2, GPU, int8 | RTX 3070 Ti 8GB | 59s | 2926 MB VRAM |
| faster-whisper large-v2, GPU, int8, batch size 8 | RTX 3070 Ti 8GB | 16s | 4500 MB VRAM |

Applicability to this app:

- The published CPU benchmark is for the `small` model, while this app currently uses `base`.
- The app runs `faster-whisper` on CPU with `compute_type="int8"`.
- Exact timing must be measured on the target laptop/server.

#### Tesseract OCR

Tesseract does not publish a simple universal latency benchmark because OCR time depends heavily on image dimensions, DPI, page layout, skew, noise, and language packs.

Relevant published guidance:

- Tesseract reads images through Leptonica-supported image formats.
- Tesseract does not directly read PDF input; PDF pages must be converted to images first.
- OCR quality is improved by clean images, deskewing, denoising, binarization, and sufficient resolution.
- The docs state that Tesseract works best on images with at least 300 DPI.

Applicability to this app:

- PDF pages are converted to images for OCR fallback.
- The app validates image pixel count and PDF page count before processing.
- Exact latency must be measured per document type.

#### all-MiniLM-L6-v2

Published model-card facts:

- maps text to a 384-dimensional dense vector
- intended for sentence and short paragraph embeddings
- input text longer than 256 word pieces is truncated by default
- model size is about 22.7M parameters

Applicability to this app:

- The app chunks extracted text before embedding.
- Chunk size is capped in `model_registry.py` to reduce truncation risk.
- Exact embedding throughput depends on CPU/GPU availability and number of chunks.

#### Cloud LLMs

Cloud providers publish context, modality, and price data, but not stable end-to-end latency guarantees for this app. Runtime depends on:

- network latency
- account tier and provider load
- prompt length
- output token count
- safety/filtering overhead
- regional endpoint behavior

For our app, cloud LLM latency must be measured through the existing processing/query flows.

### Local vs Cloud Tradeoff Matrix

| Dimension | Local tools/models | Cloud models |
|---|---|---|
| Cost per request | No API cost, but uses local CPU/RAM | Token or request-based billing |
| Privacy | Files stay local | Data sent to provider unless only extracted text/chunks are sent |
| Offline behavior | Works if dependencies/models are installed | Requires internet and API keys |
| Latency predictability | Hardware-dependent, no network dependency | Network and provider-dependent |
| Scaling | Limited by local CPU/RAM | Easier to scale via provider capacity |
| Accuracy on complex vision/audio | Can be weaker for noisy scans or difficult audio | Usually stronger for multimodal understanding |
| Input limits | Practical limits are CPU/RAM/file size | Provider token/file/page/duration limits |
| Failure mode | Missing binaries/models, slow CPU, memory pressure | API errors, rate limits, cost, network failure |

### Why Current Models Were Selected

#### Tesseract OCR for primary vision/PDF OCR

Selected because:

- local, free, and privacy-preserving
- mature OCR engine with no API dependency
- good enough for clean documents and scanned text
- avoids sending every image/PDF page to a cloud provider

Tradeoff:

- lower quality on noisy scans, handwriting, complex layouts, skewed pages, or low-resolution screenshots
- optional Gemini vision fallback exists for cases where cloud vision is acceptable

#### faster-whisper base for audio

Selected because:

- local and free after model download
- avoids sending private audio to a provider
- faster-whisper is optimized with CTranslate2 and supports CPU int8 execution
- `base` is a pragmatic balance between speed, size, and transcript quality

Tradeoff:

- local CPU transcription can still be slow for long audio
- cloud audio models could improve speed/accuracy, but add cost and privacy concerns
- app therefore enforces `MAX_AUDIO_DURATION_SEC`

#### all-MiniLM-L6-v2 for embeddings

Selected because:

- small local embedding model
- no embedding API cost
- fast enough for local semantic search
- produces compact 384-dimensional vectors
- well-suited for sentence/paragraph retrieval

Tradeoff:

- 256 word-piece truncation means chunks must stay short
- may underperform larger embedding models on complex retrieval
- app uses chunking and overlap to reduce truncation and preserve context

#### Gemini 2.5 Flash-Lite for default cloud LLM

Selected because:

- lowest-cost Gemini 2.5 production option
- large 1M token context window
- multimodal input support if vision fallback is enabled
- much cheaper than Gemini 2.5 Flash and OpenAI GPT-5 mini for output tokens
- good fit for high-volume summarization, tagging, and grounded Q&A

Tradeoff:

- cloud dependency
- quality may be lower than stronger models such as Gemini 2.5 Flash
- app uses retrieved chunks and strict prompts to keep answers grounded

#### GPT-5 mini as OpenAI fallback

Selected because:

- small OpenAI model with large context window
- useful fallback when Gemini is unavailable
- supported by the OpenAI Responses API

Tradeoff:

- more expensive than Gemini Flash-Lite for this app's expected workloads
- not used as primary default

#### GPT-5 nano not selected

Reason:

- it is cheaper than GPT-5 mini and suitable for summarization/classification tasks
- however, the app also needs grounded Q&A, where `gpt-5-mini` is a safer fallback choice
- nano can be reconsidered later for topic tags or low-risk classification-only stages

#### Gemini 2.5 Flash not selected

Reason:

- stronger candidate than Flash-Lite
- materially higher output cost than Flash-Lite
- not necessary for default accessibility pipeline tasks unless quality evaluation shows Flash-Lite is insufficient

### Application-Specific Model Guardrails

The app intentionally uses limits that are lower than provider maximums to protect local processing and keep latency predictable:

| Guardrail | Default |
|---|---:|
| Max upload size | 25 MB |
| Max audio duration | 600 seconds |
| Max PDF pages | 200 |
| Max image pixels | 40,000,000 |
| Max query length | 1,000 characters |
| Max retrieval `top_k` | 20 |
| LLM post-processing input cap | 6,000 characters |
| Q&A context cap | 12,000 characters |
| Embedding chunk size | 1,000 characters |
| Embedding chunk overlap | 200 characters |

These are app-safe limits, not hard model limits. They are chosen to prevent failures before expensive processing starts.

---

## 2. Database and Storage Decisions

### Current Persistence Stack

| Data | Current storage | Why |
|---|---|---|
| Original uploaded files | Local filesystem under `data/uploads/` | Simple, inspectable, avoids storing binary files in the DB. |
| Processed text outputs | SQLite under `data/sqlite/cas.db` | Relational metadata, durable local persistence, no server setup. |
| File metadata/status | SQLite | Easy status tracking for ingest/process/query flow. |
| Chunks and source metadata | SQLite | Supports fallback keyword search and vector re-indexing. |
| Model metrics | SQLite | Structured latency/cost/status records. |
| Dense vectors | Chroma under `data/vector_db/` | Purpose-built vector similarity search with metadata. |

### Database Candidates

| Option | Type | Strengths | Weaknesses | Fit for this app |
|---|---|---|---|---|
| SQLite | Embedded relational DB | Zero server setup, single-file DB, ACID transactions, Python stdlib support, good for local apps | Limited multi-writer concurrency, not ideal for many concurrent app servers | Best fit for local metadata and processed outputs. |
| PostgreSQL | Client/server relational DB | Strong concurrency, roles, backups, production scaling, full-text search, extensions | Requires server setup/admin, more moving parts for local project | Good future migration target for multi-user deployment. |
| PostgreSQL + pgvector | Relational + vector extension | Stores metadata and vectors in one DB, ACID, joins, vector search | Requires Postgres and extension setup, migration complexity | Best future production consolidation option. |
| Chroma | Vector database | Built for embeddings, collections, metadata filters, local/self-hosted/cloud options | Not a full relational DB replacement | Best current fit for local vector search. |
| FAISS | Vector index library | Very fast similarity search, local, mature | Lower-level library; metadata/persistence must be built separately | Good for pure vector indexing, but more custom plumbing. |
| Qdrant | Vector database | Production vector DB, filtering, scalable service | Requires service/container or managed infra | Good future vector-store upgrade. |
| Pinecone/managed vector DB | Managed vector DB | Hosted scaling and ops handled by provider | Cost, network dependency, vendor dependency | Overkill for current local-first scope. |
| Plain JSON/files | File storage | Simple for prototypes | Hard to query, weak consistency, fragile migrations | Not suitable after Phase 1. |

### SQLite Evaluation

SQLite is an embedded, serverless SQL database. It reads and writes directly to a database file, so there is no database server to install, start, configure, or administer.

Why SQLite fits the current app:

- The app is currently local-first and CLI/Streamlit-driven.
- The app needs durable structured records but not high-concurrency writes.
- Python includes `sqlite3` in the standard library.
- The DB can live under `data/sqlite/cas.db` and be copied/backed up as a file.
- File metadata, processing status, warnings, chunk metadata, and metrics map naturally to relational tables.
- SQLite is enough for one user or small local usage.

SQLite limitations:

- It is not designed as a central network database for many app servers.
- Concurrent writes are more limited than PostgreSQL.
- Operational features like roles, managed backups, replication, and observability are not comparable to PostgreSQL.
- It should be replaced if the app becomes a multi-user hosted service.

### Chroma Evaluation

Chroma is used only for vector search, not as the system-of-record database.

Why Chroma fits the current app:

- It stores embeddings and supports similarity search.
- It supports collections, metadata, and local persistence.
- It is simple to run locally compared with production vector DB services.
- It integrates well with Python RAG workflows.
- It keeps vector search concerns separate from relational metadata.

Why SQLite still stores chunks:

- SQLite remains the source of truth for chunk text and metadata.
- If Chroma is missing or partially indexed, vectors can be rebuilt from SQLite chunks.
- If Chroma fails, the app can still perform keyword fallback over stored chunks.
- UI/CLI citation display can rely on stable chunk records.

Chroma limitations:

- It is not a general-purpose relational database.
- Local Chroma is not the best final choice for many concurrent users or large multi-tenant production workloads.
- Backups/migrations need operational planning.

### Why Not PostgreSQL Yet

PostgreSQL is a strong production option, especially with `pgvector`, but it is intentionally not the Phase 1-4 default.

Reasons:

- Adds server setup and operational overhead.
- Requires DB credentials/configuration/migrations earlier than needed.
- Slows down local onboarding for a coursework/prototype-style app.
- The current workload is local-first and low-concurrency.
- SQLite + Chroma already supports the required ingest/process/query flow.

When PostgreSQL should be introduced:

- multi-user hosted deployment
- concurrent uploads/process jobs
- tenant isolation
- production authentication/authorization
- cloud backups and restore requirements
- analytics/reporting over many documents
- desire to consolidate metadata and vector search through `pgvector`

### Why Not Store Everything in Chroma

Chroma can store documents and metadata with vectors, but it should not replace the relational store here.

Reasons:

- File status transitions are relational workflow state, not vector-search state.
- Processing outputs include summaries, warnings, confidence, errors, and metrics that are easier to manage relationally.
- Model comparison metrics are naturally tabular.
- SQLite provides simpler deterministic test setup.
- Keeping chunks in SQLite enables keyword fallback and vector re-indexing.

### Why Not Store Vectors in SQLite

SQLite could store vectors as blobs/JSON, but that would not provide efficient similarity search by itself.

Reasons:

- Vector similarity search requires specialized indexing or custom scanning.
- Chroma already provides vector collections and query behavior.
- SQLite is kept focused on metadata and source-of-truth text.

### Current Storage Decision

Use a split persistence design:

```text
uploaded files -> local filesystem
metadata / outputs / chunks / metrics -> SQLite
embeddings / vector similarity index -> Chroma
```

This gives the app:

- minimal setup
- local-first execution
- durable metadata
- rebuildable vector indexes
- keyword fallback when vector search fails
- clear migration path to PostgreSQL + pgvector later

### Storage Migration Path

If the app moves to production, the recommended migration path is:

1. Move original files from local filesystem to object storage such as S3, GCS, or Azure Blob.
2. Move SQLite tables to PostgreSQL.
3. Decide whether to keep Chroma as a separate vector DB or consolidate into PostgreSQL + pgvector.
4. Add schema migrations through Alembic or a similar migration tool.
5. Add background job processing for ingestion/extraction/embedding.
6. Add tenant/user IDs to all file, processed output, chunk, and metric records.

---

## 3. Manual Benchmark Plans

### Model Benchmark Plan

Published specs are not enough for a final performance comparison. The following should be measured on the target machine and API account:

| Benchmark | Measurement |
|---|---|
| PDF direct extraction | pages/sec, total latency, text quality |
| Scanned PDF OCR | pages/sec, OCR confidence, latency by page count |
| Image OCR | latency by image resolution and OCR confidence |
| Audio transcription | seconds of audio processed per second, RAM usage, transcript quality |
| Embedding/indexing | chunks/sec, vector indexing latency |
| Query retrieval | latency for global query over N processed docs |
| Gemini answer generation | latency, input/output tokens, cost estimate, answer quality |
| OpenAI fallback answer generation | latency, input/output tokens, cost estimate, answer quality |
| End-to-end flow | ingest + process + query latency per file type |

Suggested test set:

- clean text PDF, 5 pages
- scanned PDF, 10 pages
- large PDF near `MAX_PDF_PAGES`
- screenshot image, low/medium/high resolution
- clear 1-minute audio
- noisy 5-minute audio
- multi-document query over 3 to 5 processed docs

### Database Benchmark Plan

Published database characteristics are not enough for final performance claims. For this app, benchmark:

| Benchmark | Measurement |
|---|---|
| SQLite insert throughput | Time to ingest metadata for N files. |
| SQLite processed-output write | Time to save large processed outputs. |
| SQLite chunk write | Time to save N chunks. |
| Chroma indexing | Time to embed and add N chunks. |
| Chroma query | Search latency for one file and all files. |
| Keyword fallback | SQLite fallback search latency over N chunks. |
| Re-index path | Time to rebuild Chroma from SQLite chunks. |
| DB size growth | SQLite and Chroma disk growth per document/page/chunk. |

Suggested benchmark sizes:

- 1 document, 10 chunks
- 10 documents, 250 chunks
- 100 documents, 5,000 chunks
- 1,000 documents, 50,000 chunks

---

## Source Links

### Model and AI Tool Sources

- Gemini 2.5 Flash-Lite model specs: https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash-lite
- Gemini 2.5 Flash model specs: https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash
- Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
- OpenAI GPT-5 mini model specs: https://platform.openai.com/docs/models/gpt-5-mini
- OpenAI GPT-5 nano model specs: https://platform.openai.com/docs/models/gpt-5-nano
- OpenAI pricing: https://platform.openai.com/docs/pricing
- all-MiniLM-L6-v2 model card: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- faster-whisper benchmarks: https://github.com/SYSTRAN/faster-whisper
- Tesseract OCR quality guidance: https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html
- Tesseract input formats: https://tesseract-ocr.github.io/tessdoc/InputFormats.html

### Database and Storage Sources

- SQLite appropriate uses: https://www.sqlite.org/whentouse.html
- SQLite serverless design: https://www.sqlite.org/serverless.html
- SQLite zero-configuration: https://sqlite.org/zeroconf.html
- SQLite overview: https://www.sqlite.org/about.html
- Chroma introduction: https://docs.trychroma.com/
- Chroma collections: https://docs.trychroma.com/docs/collections/manage-collections
- Chroma embedding functions: https://docs.trychroma.com/docs/embeddings/embedding-functions
- Chroma persistent client example: https://cookbook.openai.com/examples/vector_databases/chroma/using_chroma_for_embeddings_search
- PostgreSQL full-text search: https://www.postgresql.org/docs/current/textsearch-intro.html
- pgvector: https://github.com/pgvector/pgvector
