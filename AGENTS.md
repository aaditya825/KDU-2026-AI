# KDU-2026-AI

Instructions for coding agents working in this repository.

## Project Purpose

Build a context-aware hybrid-search RAG chatbot with a Streamlit UI. The system ingests PDFs and blog URLs, performs contextual chunking, combines semantic and keyword retrieval, reranks candidate chunks, and generates grounded answers with citations.

## Source of Truth

Read these files before making architectural or implementation decisions:

- `docs/requirements.txt`
- `docs/LLD_v1.md`
- `docs/implementation_decisions.md`

If code and docs disagree, treat `docs/implementation_decisions.md` as the locked implementation default unless the user explicitly changes it.

## Current Repository Status

- The repository is currently documentation-first.
- Major implementation work will scaffold the project from the LLD.
- Do not assume existing source folders already exist.
- Create structure deliberately instead of improvising ad hoc file placement.

## Locked Implementation Defaults

Unless the user says otherwise, use these defaults:

- UI: `Streamlit`
- Vector store: `ChromaDB`
- Keyword retrieval: `BM25`
- Embeddings: `sentence-transformers`
- Generator: Gemini chat model
- Reranker: cross-encoder reranker
- Chunking: contextual chunking, `chunk_size=512`, `overlap=50`
- Hybrid retrieval: semantic top-10 + keyword top-10, RRF fusion, rerank fused top-10, generate from reranked top-5

Do not silently swap these defaults. If you change them, update `docs/implementation_decisions.md` in the same task.

## Expected Project Layout

Target the structure described in `docs/LLD_v1.md`:

- `src/core/` for interfaces, models, and config
- `src/ingestion/` for loaders, chunkers, embedders, and ingestion pipeline
- `src/storage/` for vector and keyword persistence
- `src/retrieval/` for retrievers, fusion, rerankers, and retrieval pipeline
- `src/generation/` for LLM adapters, prompts, context building, and response generation
- `src/orchestration/` for end-to-end workflow coordination
- `src/utils/` for shared helpers
- `ui/` for Streamlit app and UI components
- `tests/` for unit and integration coverage
- `config/` for app configuration
- `data/` for local storage artifacts

Keep concerns separated. Do not put business logic inside the Streamlit layer.

## Agent Workflow

For any non-trivial task:

1. Read the relevant docs first.
2. Confirm whether the task is scaffold, ingestion, retrieval, generation, or testing work.
3. Reuse existing interfaces and models instead of duplicating types.
4. Make the smallest coherent change that moves the system forward.
5. Run the most relevant validation available after edits.
6. Report assumptions, especially when code is still being scaffolded.

## Coding Rules

- Prefer Python for the application code unless the user explicitly requests otherwise.
- Keep all major components behind interfaces so providers can be swapped later.
- Use explicit constructor injection for cross-component dependencies.
- Keep models and payload contracts stable across layers.
- Preserve source traceability on every chunk and response citation path.
- Avoid hidden global state except for configuration loading where necessary.
- Do not hardcode secrets, API keys, or machine-specific paths into project code.
- Keep Streamlit callbacks thin and push logic into services or orchestration classes.

## Data and Retrieval Rules

- Normalize all inputs into a common `Document` model.
- Every chunk must keep `document_id`, `chunk_id`, ordering, and source metadata.
- Deduplicate hybrid retrieval results by `chunk_id`.
- Preserve raw retrieval scores or provenance where useful for debugging.
- If reranking is unavailable, degrade gracefully to fused ranking.
- If retrieved context is insufficient, generate an explicit “insufficient context” style answer instead of fabricating.

## Testing Expectations

When code exists, prefer these checks:

- Unit tests for loaders, chunkers, retrievers, rerankers, and generation helpers
- Integration tests for ingestion and retrieval pipelines
- Focused tests for any changed module before broad test runs

Minimum expectations for meaningful feature work:

- new logic has tests or a documented reason why it does not
- retrieval changes validate ordering, not just result presence
- generation changes validate citation or source behavior

## Commands

Use the actual repo commands if they exist. If the scaffold is not present yet, create the code first and then add/update the command section.

Expected future commands:

- install dependencies: `pip install -r requirements.txt`
- run app: `streamlit run ui/app.py`
- run tests: `pytest`
- run a focused test file: `pytest tests/unit/test_<module>.py`

Do not invent passing results for commands that cannot yet run.

## Configuration and Secrets

- Keep secrets in `.env`.
- Keep runtime defaults in `config/config.yaml`.
- Treat UI-level settings as session overrides, not permanent config changes.
- Never print secrets into logs, tests, or fixtures.

## Documentation Rules

- If you make an architectural decision not already captured, update `docs/implementation_decisions.md`.
- If the code structure diverges from `docs/LLD_v1.md`, either align the code or document the divergence clearly.
- Keep documentation concise and implementation-focused.

## What to Avoid

- Do not introduce new providers or frameworks without need.
- Do not bypass interfaces with direct cross-layer coupling.
- Do not mix ingestion, retrieval, and UI concerns in a single module.
- Do not claim end-to-end completion without validating the relevant flow.
- Do not delete or override user-authored documentation without explicit instruction.
