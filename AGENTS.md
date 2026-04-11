# Repository Guidance

## Purpose
This repository is building the **Hybrid Service Layer + LCEL Skeleton** implementation documented in [04_hybrid_service_lcel_mvp.md](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\docs\mvp_approaches\04_hybrid_service_lcel_mvp.md).

Current phase:

- Phase 1 only: text-only assistant
- Frontend: Streamlit
- Backend: FastAPI
- LLM integration: LangChain

Do not implement later-phase features until the current phase is working end to end unless the task explicitly asks for them.

## System of record
Read these first before changing architecture:

- [00_comparison.md](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\docs\mvp_approaches\00_comparison.md)
- [04_hybrid_service_lcel_mvp.md](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\docs\mvp_approaches\04_hybrid_service_lcel_mvp.md)

If code and docs diverge, update the docs or state the mismatch explicitly before expanding the design.

## Target repository layout

```text
src/
  assistant/
    frontend/
      streamlit_app.py
    backend/
      main.py
      api/
        routers/
          assistant.py
      contracts/
        requests.py
        responses.py
      orchestrator/
        assistant_orchestrator.py
      application/
        use_cases/
          text_chat.py
        services/
          input_normalizer.py
          route_resolver.py
          prompt_factory.py
          response_formatter.py
      chains/
        general_text_chain.py
      infrastructure/
        llm/
          model_selector.py
          anthropic_gateway.py
      shared/
        settings.py
        exceptions.py
```

## Architecture rules

### 1. Keep the frontend thin
The Streamlit app is a view and interaction layer only.

- no LangChain logic in the frontend
- no prompt construction in the frontend
- no provider-specific model code in the frontend
- frontend state belongs in `st.session_state`

### 2. Keep the API layer thin
FastAPI routers should:

- validate request and response models
- call the orchestrator
- translate exceptions into HTTP responses

Do not place business logic inside route handlers.

### 3. The orchestrator is the backend entry point
`AssistantOrchestrator` coordinates:

- input normalization
- route resolution
- use-case dispatch
- response formatting

It should not absorb provider-specific details or large prompt bodies.

### 4. One use case per capability
Use cases should map to business capabilities, not technical layers.

Initial use case:

- `TextChatUseCase`

Later use cases:

- `WeatherUseCase`
- `ImageAnalysisUseCase`

### 5. Chain composition belongs near the use case
Keep LCEL chain composition in:

- `backend/chains/`
- or inside a use case when it is still very small

Do not spread chain assembly across routers, frontend code, and infrastructure modules.

### 6. Provider-specific code stays in infrastructure
Anything tied to Anthropic, OpenAI, or another provider belongs in:

- `backend/infrastructure/llm/`

The rest of the application should depend on narrow interfaces or service methods, not on concrete provider setup.

### 7. Add seams only when they are useful
This repo already keeps these early seams:

- `InputNormalizer`
- `RouteResolver`
- `AssistantOrchestrator`

Do not add `ToolRegistry`, `MemoryProvider`, or `ProfileProvider` until the relevant feature lands.

## Implementation rules

- Prefer explicit typed request and response models with Pydantic.
- Use clear, descriptive module names over clever abstractions.
- Default to simple synchronous flows until streaming or async becomes necessary.
- Keep functions and methods short enough that their control flow is obvious.
- Prefer one responsibility per file when practical.
- Use `ChatPromptTemplate` and LCEL composition for LangChain code.
- Prefer structured outputs once response fields become stable.
- For multimodal work later, use multimodal content blocks inside `HumanMessage`; do not design around a separate `ImageContent` abstraction.

## Feature rollout order

1. Text-only general chat
2. Structured output
3. User profile injection
4. Weather tool
5. Conversation memory
6. Image upload and analysis
7. Dynamic style and model switching
8. Observability hardening

## Testing expectations

- Add unit tests for each new service or use case with meaningful behavior.
- Add integration tests for the FastAPI endpoint once the API exists.
- Keep the first test suite simple and local.
- Avoid network-dependent tests when a mock or fake is sufficient.

## Skills available in this repo
Project-local skills live under `.agents/skills/`.

Use these when relevant:

- `$assistant-architecture`
- `$fastapi-assistant-backend`
- `$streamlit-chat-frontend`
- `$langchain-lcel-assistant-flow`

## When to update this file
Update `AGENTS.md` when:

- the system-of-record architecture changes
- the project reaches a new feature phase
- directory conventions change
- new mandatory commands or validation steps are introduced
