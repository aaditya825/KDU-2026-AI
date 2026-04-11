# Backend Guidance

This file applies to `src/assistant/backend/`.

## Backend responsibilities
The backend owns:

- API contracts
- orchestration
- use-case execution
- LangChain integration
- provider integration
- response shaping

The backend does not own Streamlit presentation logic.

## Module boundaries

### `api/routers/`
- HTTP transport only
- validate request and response models
- call orchestrator methods
- no prompt logic
- no provider setup

### `contracts/`
- Pydantic request and response models
- backend-facing transport contracts

### `orchestrator/`
- request coordination layer
- normalize request
- resolve route
- dispatch use case
- format response

### `application/use_cases/`
- one business capability per use case
- keep capability logic readable and explicit

### `application/services/`
- reusable backend services such as:
  - `input_normalizer`
  - `route_resolver`
  - `prompt_factory`
  - `response_formatter`

### `chains/`
- LCEL chain builders
- prompt plus model composition
- structured-output wrappers when needed

### `infrastructure/llm/`
- provider-specific model initialization
- API key consumption
- model selection policies

### `shared/`
- config, constants, exceptions

## Backend implementation rules

- Start with a single active route: `general_text`.
- Keep `RouteResolver` trivial until a second route exists.
- Keep the first LangChain path synchronous and explicit.
- Prefer small service classes or simple functions over deep inheritance.
- Do not introduce background tasks, queues, or database persistence until they are required by a feature.
- When adding memory later, wrap the selected chain with `RunnableWithMessageHistory` rather than mixing history storage into use-case logic.
- When adding tools later, use `.bind_tools()` and keep tool definitions outside the orchestrator.

## Required quality bar

- all new public functions should be typed
- request and response models should be explicit
- exceptions should be translated into stable API behavior
- do not leak provider-specific response objects to the router layer

## Growth path
Extend the backend in this order:

1. `TextChatUseCase`
2. structured output
3. profile-aware prompt enrichment
4. weather use case
5. memory wrapping
6. image analysis use case
7. model and style policies
