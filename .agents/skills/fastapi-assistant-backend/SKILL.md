---
name: "fastapi-assistant-backend"
description: "Use when implementing or modifying the FastAPI backend for this assistant, including routers, contracts, orchestrator, use cases, backend services, and infrastructure-backed LLM integration."
---

# FastAPI Assistant Backend

Use this skill for backend work under `src/assistant/backend/`.

## Read first
- [AGENTS.md](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\AGENTS.md)
- [src/assistant/backend/AGENTS.md](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\AGENTS.md)
- [04_hybrid_service_lcel_mvp.md](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\docs\mvp_approaches\04_hybrid_service_lcel_mvp.md)

## Use this skill when
- creating or editing FastAPI routes
- defining request and response models
- implementing `AssistantOrchestrator`
- implementing backend services or use cases
- wiring LangChain-backed model access into the backend

## Backend workflow

1. Start from the contract.
   - define or update the request and response schemas first

2. Keep the router thin.
   - validate
   - call orchestrator
   - return typed response

3. Put flow coordination in the orchestrator.
   - normalize request
   - resolve route
   - dispatch use case
   - format response

4. Put capability logic in a use case.
   - one capability per use case
   - keep it readable

5. Put provider details in infrastructure.
   - model initialization
   - auth
   - provider-specific config

## Code expectations

- prefer explicit classes or simple functions over deep abstraction
- use type hints on public methods
- use Pydantic for HTTP contracts
- keep route handlers short
- keep chain assembly localized

## Testing guidance

- unit test the use case and services first
- add API integration tests once routes exist
- use mocks or fakes for external model calls when possible

## Guardrails

- no prompt strings in route handlers
- no provider response objects leaving infrastructure untouched
- no frontend concerns in backend modules
