# Claude Code Usage Guide for Content Accessibility Suite

## Purpose

This guide keeps future Claude Code sessions aligned with the implemented backend decisions. The current source of truth is:

- `CLAUDE.md`
- `Docs/handoff_summary.md`
- `Docs/content_accessibility_suite_implementation_plan.md`
- `Docs/content_accessibility_suite_low_level_design.md`
- `Docs/architecture_decision_comparison.md`
- `app/config/model_registry.py`

## Current Project Rules

- Backend-first: verify behavior through CLI before changing Streamlit behavior.
- Streamlit is implemented as a thin UI over existing controllers.
- Ingest and process one file at a time.
- Query across all processed documents by default.
- Use `--file-id` only for scoped search/query.
- Route files by detected MIME/content, not extension-first logic.
- Keep model declarations in `app/config/model_registry.py`.
- Supported cloud providers are Gemini and OpenAI only.
- Do not add Groq or OpenRouter.
- Use Gemini `gemini-2.5-flash-lite` by default and OpenAI `gpt-5-mini` as optional fallback.
- Use `google-genai` for Gemini.
- Preserve fallback behavior for embedding/vector/LLM failures.

## Standard Verification Commands

```powershell
python -m pytest -q -p no:cacheprovider
python -m app.cli --help
python -m app.cli ingest <file_path>
python -m app.cli process <file_id>
python -m app.cli query "What are the key requirements?"
python -m app.cli search "requirements"
python -m app.cli compare <file_id>
```

## Phase Prompts

### Phase 1

```text
Implement or verify Phase 1 only.
Respect the current decisions: content-based MIME detection, one-file ingestion, SQLite metadata, and CLI-first verification.
Verify with:
python -m app.cli ingest <file_path>
python -m pytest -q -p no:cacheprovider
```

### Phase 2

```text
Implement or verify Phase 2 only.
Processing must use the content router and modality pipelines.
Persist extraction method, confidence, warnings, page metadata, latency, and errors.
Verify with:
python -m app.cli process <file_id>
python -m pytest -q -p no:cacheprovider
```

### Phase 3

```text
Implement or verify Phase 3 only.
Queries should search all processed documents by default.
Answers must be grounded in retrieved chunks and show supporting chunks.
Semantic retrieval should fall back to keyword search if embeddings or Chroma fail.
Verify with:
python -m app.cli query "question"
python -m app.cli search "query"
python -m app.cli compare <file_id>
python -m pytest -q -p no:cacheprovider
```

### Phase 4

```text
Implement or polish Phase 4 only.
Keep Streamlit as a thin layer over existing controllers.
Preserve one-file processing and cross-document query behavior.
Show answer plus supporting chunks in the UI.
Add report/export generation under reports/ if that is the assigned scope.
Verify CLI still passes before checking Streamlit.
```

## Useful Maintenance Checks

Check removed providers do not reappear:

```powershell
rg -n "groq|openrouter|OPENROUTER|GROQ" app tests requirements.txt .env.example
```

Docs may mention Groq/OpenRouter only to document that they are excluded. Runtime code and environment files should not include provider integration or keys for them.

Note: `rg` may be unavailable on some Windows setups. Use PowerShell `Select-String` as fallback.

Check model IDs are centralized:

```powershell
rg -n "gpt-|gemini-|all-MiniLM" app
```

Expected runtime model IDs should appear in `app/config/model_registry.py`; descriptive docs/comments are acceptable.

Check file routing stays content-based:

```powershell
rg -n "detect_mime_type|resolve_file_type|suffix|extension" app/services app/storage
```

## Handoff Summary Format

When ending a phase or major fix, summarize:

- files changed
- behavior changed
- commands run
- tests passed
- known limitations
- next entry point
