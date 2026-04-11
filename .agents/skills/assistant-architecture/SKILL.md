---
name: "assistant-architecture"
description: "Use when planning, scaffolding, or refactoring this repository's architecture for the Streamlit + FastAPI + LangChain assistant. Trigger when adding a new feature slice, changing module boundaries, or checking whether a code change still follows the hybrid service-layer plus LCEL skeleton design."
---

# Assistant Architecture

Use this skill for repository-level architecture work in this project.

## Read first
- [AGENTS.md](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\AGENTS.md)
- [04_hybrid_service_lcel_mvp.md](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\docs\mvp_approaches\04_hybrid_service_lcel_mvp.md)
- [00_comparison.md](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\docs\mvp_approaches\00_comparison.md)

## Use this skill when
- creating the initial project scaffold
- deciding where new files belong
- reviewing whether a change fits the agreed architecture
- adding the next feature phase without collapsing boundaries

## Core rules

1. Keep the current phase small.
   - Build only the feature slice requested.
   - Do not add future subsystems just because they are expected later.

2. Preserve the request flow.
   - FastAPI router
   - `AssistantOrchestrator`
   - `InputNormalizer`
   - `RouteResolver`
   - use case
   - response formatter

3. Keep boundaries explicit.
   - frontend is UI only
   - routers are transport only
   - orchestrator coordinates
   - use cases own business capabilities
   - provider-specific setup stays in infrastructure

4. Add extension seams only when the next feature actually needs them.
   - add `ProfileProvider` only when personalization lands
   - add `ToolRegistry` only when tools land
   - add `MemoryProvider` only when memory lands

## Decision checklist
Before adding a new module, answer these:

- Is this file useful in the current phase, or only hypothetical?
- Does this logic belong in the frontend, router, orchestrator, use case, service, chain, or infrastructure?
- Will this change make the request path easier or harder to follow?
- Can the same result be achieved with one fewer abstraction?

## Expected output
When using this skill, prefer:

- updated folder structure
- small architectural diffs
- direct statements about module ownership
- explicit migration path for the next feature

## Guardrails

- Do not put LangChain logic into Streamlit.
- Do not put business logic into FastAPI routers.
- Do not let the orchestrator become a catch-all service class.
- Do not create generic base classes without at least two real uses.
