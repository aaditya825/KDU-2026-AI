# Implementation Decisions for Hybrid-Search RAG Chatbot

This document captures the assumed implementation decisions derived from [requirements.txt](/C:/Users/Dell/Desktop/Phase3-AI/KDU-2026-AI/docs/requirements.txt) and the current [LLD_v1.md](/C:/Users/Dell/Desktop/Phase3-AI/KDU-2026-AI/docs/LLD_v1.md). These decisions should be treated as locked unless explicitly changed later.

## 1. Default Tech Stack

- Use `Streamlit` for the user interface.
- Use `ChromaDB` as the default local vector database.
- Use `BM25` as the keyword retrieval mechanism.
- Use `sentence-transformers` as the default embedding provider.
- Use a Gemini chat model as the default answer-generation model.
- Keep all major components behind interfaces so other providers can be swapped later.

## 2. Embedding and Reranking Defaults

- Use a `sentence-transformers` model as the default embedding implementation.
- Keep OpenAI embeddings as an optional alternative behind the same embedder interface.
- Make reranking mandatory in the retrieval flow.
- Use a cross-encoder reranker as the default reranking implementation.
- If the reranker is unavailable, fall back to fused hybrid ranking instead of failing the query.

## 3. Data Model Contracts

### `Document`

Required fields:

- `document_id`
- `source_type`
- `source`
- `title`
- `content`
- `metadata`
- `created_at`

### `Chunk`

Required fields:

- `chunk_id`
- `document_id`
- `text`
- `position`
- `start_offset`
- `end_offset`
- `section_title`
- `metadata`

### `Query`

Required fields:

- `query_text`
- `top_k`
- `filters`
- `session_id`

### `Response`

Required fields:

- `answer`
- `sources`
- `retrieved_chunks`
- `latency_ms`
- `metadata`

## 4. Chunking Behavior

- Use contextual chunking as the default chunking strategy.
- Use section-aware splitting wherever possible.
- Set `chunk_size = 512`.
- Set `overlap = 50`.
- Preserve neighboring context using overlap and section metadata.
- Never emit a chunk without source traceability metadata.

## 5. Hybrid Retrieval Behavior

- Run semantic retrieval with `top_k = 10`.
- Run keyword retrieval with `top_k = 10`.
- Deduplicate results using `chunk_id`.
- Fuse semantic and keyword results using Reciprocal Rank Fusion (RRF).
- Pass fused top-10 candidates to the reranker.
- Keep reranked top-5 chunks for final answer generation.

## 6. Storage and Persistence

- Both vector and keyword indexes must persist locally across application restarts.
- Re-ingesting the same document should update or replace previous entries for that `document_id`.
- Re-ingestion should not create uncontrolled duplicates.
- Stored vectors, chunk metadata, and keyword entries must remain aligned through `chunk_id` and `document_id`.

## 7. Document Ingestion Rules

- Support only PDFs and blog URLs in the first implementation.
- Allow multiple documents to be active in the same session.
- URL ingestion must extract readable article text and headings.
- PDF ingestion must preserve document order and page-level metadata where available.
- All ingested content must be normalized into the same `Document` model before chunking.

## 8. Prompting and Response Policy

- The LLM must answer only from retrieved context.
- If the retrieved context is insufficient, the response must explicitly say that the answer is not available from the provided sources.
- Every answer must include citations.
- Citations must reference document title or source and chunk position.
- Only the reranked final chunk set should be sent to the generator.

## 9. UI Workflow Assumptions

- The user uploads a PDF or submits a blog URL.
- The system ingests, chunks, embeds, and indexes the document.
- The user asks questions in the same Streamlit session.
- Chat operates over the currently ingested document set for that session.
- The UI must show:
  - uploaded or active sources
  - answer text
  - citations
  - basic retrieval or latency metrics

## 10. Configuration Contract

- `.env` stores secrets such as API keys.
- `config.yaml` stores default runtime configuration.
- UI controls may override retrieval and generation settings only for the active session.
- Configuration precedence must be:
  1. active UI session overrides
  2. `.env` for secrets
  3. `config.yaml` defaults

## 11. Testing Expectations

- Unit tests must cover:
  - loaders
  - chunkers
  - retrievers
  - generator logic
- Integration tests must cover:
  - ingestion pipeline
  - retrieval pipeline
- Minimum acceptance criteria:
  - documents ingest successfully
  - hybrid retrieval returns relevant chunks
  - reranking narrows results appropriately
  - grounded answers are produced with citations

## 12. Error Handling and Logging

- Catch and surface ingestion failures with user-readable messages.
- Catch and surface malformed file or URL handling failures.
- Handle empty retrieval results gracefully.
- Catch and surface LLM or API failures without crashing the app.
- Log structured events for:
  - ingestion
  - chunking
  - retrieval
  - reranking
  - generation

## 13. Summary

These decisions make the current LLD implementation-ready by locking the main defaults, contracts, retrieval flow, response behavior, UI assumptions, and acceptance expectations required to build the assignment in a consistent way.
