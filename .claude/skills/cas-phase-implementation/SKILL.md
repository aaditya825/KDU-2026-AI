---
name: cas-phase-implementation
description: Implement one phase of the Content Accessibility Suite plan. Use when the user asks to build a phase, continue implementation, or execute the backend-first assignment plan.
disable-model-invocation: true
---

# Content Accessibility Suite Phase Implementation

Use this skill to implement exactly one phase from `Docs/content_accessibility_suite_implementation_plan.md`.

## Required Context

Read these files first:

1. `Docs/requirements.txt`
2. `Docs/content_accessibility_suite_low_level_design.md`
3. `Docs/content_accessibility_suite_implementation_plan.md`
4. `CLAUDE.md`

## Execution Rules

- Implement only the requested phase.
- Preserve one-file-at-a-time behavior.
- Phases 1-3 must be backend and CLI first.
- Do not add Streamlit before phase 4.
- Keep provider-specific logic behind adapters.
- Keep generated runtime data under ignored runtime folders such as `data/`.
- Never hardcode secrets.
- For PDF/image extraction, preserve confidence and uncertainty metadata.
- For Q&A, retrieve chunks first and generate answers only from retrieved context.

## Workflow

1. Inspect the current repository state and identify which phase artifacts already exist.
2. Create a short checklist for the active phase.
3. Implement the smallest complete backend slice for that phase.
4. Add or update focused tests where practical.
5. Run the narrowest useful CLI/test verification.
6. Summarize:
   - files changed,
   - commands run,
   - what works,
   - what remains for the next phase.

## Phase Boundaries

- Phase 1: backend skeleton, config, validation, storage, metadata, `ingest` CLI.
- Phase 2: extraction pipelines, adapters, post-processing, generated outputs, confidence handling, `process` CLI.
- Phase 3: chunking, embeddings, Chroma, search, grounded Q&A, model comparison, `search`, `ask`, and `compare` CLI.
- Phase 4: Streamlit UI, reports, README, final tests, submission polish.

## Completion Standard

A phase is complete only when its CLI or UI acceptance path from the implementation plan works or has a clearly documented blocker.
