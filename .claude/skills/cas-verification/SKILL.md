---
name: cas-verification
description: Verify a Content Accessibility Suite phase with focused checks. Use before declaring a phase complete, after implementation changes, or when debugging assignment deliverables.
disable-model-invocation: true
---

# Content Accessibility Suite Verification

Use this skill to validate that the current implementation matches the phase plan.

## Required Context

Read:

1. `Docs/content_accessibility_suite_implementation_plan.md`
2. `CLAUDE.md`
3. Relevant source files for the active phase

## Verification Rules

- Prefer narrow, phase-specific checks before broad checks.
- For phases 1-3, verify through CLI commands before considering UI.
- For phase 4, verify both CLI and Streamlit behavior.
- Do not mark a phase complete if the implementation accepts multiple input files at once.
- Do not mark grounded Q&A complete unless answers cite or show supporting chunks.
- Do not mark extraction complete unless low-confidence/uncertain extraction is represented in outputs.

## Suggested Checks

### Phase 1

```bash
python -m app.cli --help
python -m app.cli ingest sample_doc.txt
```

Confirm validation rejects unsupported files when expected.

### Phase 2

```bash
python -m app.cli process <file_id>
```

Confirm extracted text, cleaned text, summary, key points, tags, confidence, and timing are visible or persisted.

### Phase 3

```bash
python -m app.cli search <file_id> "query text"
python -m app.cli ask <file_id> "question"
python -m app.cli compare <file_id>
```

Confirm retrieved chunks are used before answer generation.

### Phase 4

```bash
streamlit run app/main.py
```

Confirm UI is a thin layer over backend services and supports one active file.

## Report Format

Return:

- checks run,
- pass/fail result,
- blockers,
- exact next fix if failed.
