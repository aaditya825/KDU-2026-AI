# Low-Level Design: MVP Approach 4 - Hybrid Service Layer + LCEL Skeleton

## 1. Goal of this MVP
Build the first feature as a text-only assistant, but shape the codebase so the next features can be added incrementally with minimal churn.

This approach intentionally combines:

- the readability and SOLID-friendly module boundaries of Approach 2
- the orchestrator-first and extension-ready request flow of Approach 3

This MVP implements:

- Streamlit frontend
- FastAPI backend
- one text-only general chat flow
- structured API response
- orchestrator entry point
- normalized request state
- route selection seam, even though only one route is active

This MVP does **not** implement yet:

- image upload
- weather tool
- conversation memory
- user profile injection
- dynamic style switching
- model switching by task

But it is explicitly designed so those features can be added in small, separate increments.

## 2. Why this is the best combined approach
Approach 2 was strong because it kept the code approachable and easy to test. Approach 3 was strong because it introduced the long-term system shape early. This hybrid keeps both benefits while removing the weakest parts of each:

- from Approach 2, it keeps clear use cases, service boundaries, and simple folders
- from Approach 3, it keeps the orchestrator, input normalization, and a future-ready route seam
- unlike Approach 3, it does **not** create too many empty placeholders too early
- unlike Approach 2, it does **not** delay the orchestration model until a later refactor

The result is a backend that is still easy to understand for a beginner, but does not need a large structural rewrite when you add weather, memory, or multimodal processing.

## 3. Architecture

```text
Streamlit UI
    |
    v
FastAPI Router
    |
    v
AssistantOrchestrator
    |
    v
InputNormalizer
    |
    v
RouteResolver  ------------------- future: weather_text, image_analysis
    |
    v
TextChatUseCase
    |-------------------------|
    v                         v
PromptFactory            ModelSelector
    |                         |
    -------- LCEL Chain -------
               |
               v
ResponseFormatter
               |
               v
FastAPI Response Model
               |
               v
Streamlit Render
```

Future-ready seams that exist now, but stay very light:

- `RouteResolver` currently resolves only `general_text`
- `InputNormalizer` currently handles only text requests
- `ModelSelector` currently returns one default model
- `ResponseFormatter` currently maps a simple text response

Future seams added only when needed:

- `ProfileProvider`
- `MemoryProvider`
- `ToolRegistry`

## 4. Design principles behind this approach

### 4.1 Simple first, extensible second
Every component in the MVP should already be useful on day one. We avoid creating empty "future folders" unless they help readability now.

### 4.2 Explicit request flow
The request should move through a visible sequence:

- normalize input
- resolve route
- execute use case
- format response

That makes the code easier to debug than a hidden all-in-one service.

### 4.3 SOLID without over-abstraction
We use interfaces and boundaries only where they clarify the code:

- route resolution is separate from use-case execution
- model selection is separate from prompt building
- response formatting is separate from chain execution

But we do **not** create many generic base classes unless there is already more than one concrete implementation.

## 5. Core components

### 5.1 Streamlit Frontend
Purpose:

- collect user input
- call the backend
- display typed responses

Responsibilities:

- render the chat UI
- store transient UI state in `st.session_state`
- send a simple HTTP request to FastAPI
- later accept file uploads without changing the whole app layout

### 5.2 FastAPI Router
Purpose:

- act as the HTTP boundary for the backend

Responsibilities:

- expose `/assistant/chat`
- validate request and response models
- delegate work to the orchestrator
- translate exceptions into HTTP responses

### 5.3 AssistantOrchestrator
Purpose:

- serve as the main backend entry point for the assistant

Responsibilities:

- receive the request from the API layer
- normalize the incoming payload
- ask the route resolver which use case should handle it
- delegate to the selected use case
- format the final response

Why it belongs in the MVP:

- it introduces the final system shape early
- it keeps the API layer thin
- it gives a natural place to plug in memory, profiles, and tools later

### 5.4 InputNormalizer
Purpose:

- convert raw request data into a consistent internal shape

Responsibilities:

- validate and normalize text input
- produce a normalized request object or state dictionary
- later support image bytes, uploaded file metadata, and hidden user context

Why it matters now:

- it prevents the route layer and use case from dealing with transport-specific payloads

### 5.5 RouteResolver
Purpose:

- decide which use case should handle the request

Responsibilities:

- currently return `general_text`
- later resolve `weather_text`, `image_analysis`, and other routes

Why it stays very small in the MVP:

- it is just a seam today, not a full routing engine
- later it can become a `RunnableBranch`-backed or policy-driven resolver

### 5.6 TextChatUseCase
Purpose:

- implement the only active business capability in this MVP

Responsibilities:

- request the prompt from `PromptFactory`
- request the model from `ModelSelector`
- build and invoke the LCEL chain
- return the raw chain output

### 5.7 PromptFactory
Purpose:

- keep prompt construction separate from orchestration and provider logic

Responsibilities:

- build the system and human prompt for general text chat
- later support style-aware and route-specific prompts

### 5.8 ModelSelector
Purpose:

- centralize model selection decisions

Responsibilities:

- return the default model in the MVP
- later switch models by route, complexity, or modality

### 5.9 ResponseFormatter
Purpose:

- convert chain output into a stable API response schema

Responsibilities:

- normalize model output into `AssistantResponse`
- keep response shape stable for the Streamlit frontend
- later enforce route-specific structured outputs

## 6. How the MVP works step by step

1. The user enters a text message in Streamlit.
2. Streamlit sends a request to `POST /assistant/chat`.
3. FastAPI validates the request body with a Pydantic model.
4. The router passes the validated request to `AssistantOrchestrator`.
5. The orchestrator calls `InputNormalizer`.
6. `InputNormalizer` returns a normalized request state.
7. The orchestrator asks `RouteResolver` for the route.
8. `RouteResolver` returns `general_text`.
9. The orchestrator invokes `TextChatUseCase`.
10. `TextChatUseCase` builds the LCEL chain using `PromptFactory` and `ModelSelector`.
11. The chain runs with `.invoke()`.
12. The orchestrator passes the raw result to `ResponseFormatter`.
13. The formatter returns a typed response model.
14. FastAPI returns JSON.
15. Streamlit renders the response.

## 7. LangChain usage in this MVP

### Actively used now
- `ChatPromptTemplate`
- one chat model via LangChain integration
- the LCEL pipe operator
- `.invoke()`
- optionally `.with_structured_output()` if you want structured response fields immediately

### Intentionally deferred, but planned for
- `RunnableBranch` once more than one route is active
- `RunnableWithMessageHistory` once memory is added
- `.bind_tools()` once weather and other tools are introduced
- multimodal `HumanMessage` content blocks once image input is added

## 8. Pros
- cleaner than the vertical slice
- more future-ready than the pure service-layer MVP
- introduces the orchestrator early without overbuilding the system
- easy to test component-by-component
- very suitable for incremental delivery

## 9. Cons
- slightly more structure than a minimal MVP
- one extra layer, the orchestrator, may feel unnecessary until the second feature is added
- requires discipline to keep future seams lightweight until needed

## 10. Ideal folder structure

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
          prompt_factory.py
          route_resolver.py
          input_normalizer.py
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

## 11. Why this folder structure is the right compromise

### Keeps the useful boundaries from Approach 2
- API
- contracts
- application services
- use case
- infrastructure

### Keeps the most valuable extension points from Approach 3
- dedicated orchestrator
- input normalization seam
- route resolution seam
- chain builder module

### Avoids premature modules
Not added yet:

- `tools/`
- `memory/`
- `profiles/`
- `input/image_normalizer.py`

Those are added only when the next relevant feature lands.

## 12. Module-by-module explanation

### `frontend/streamlit_app.py`
- renders the UI
- makes backend calls
- owns only presentation logic

### `backend/main.py`
- creates the FastAPI app
- wires the API router

### `backend/api/routers/assistant.py`
- defines the assistant endpoint
- delegates to `AssistantOrchestrator`

### `backend/contracts/requests.py`
- request schemas such as `AssistantChatRequest`

### `backend/contracts/responses.py`
- response schemas such as `AssistantResponse`

### `backend/orchestrator/assistant_orchestrator.py`
- main application coordinator
- the best place to later add profiles, memory, and route dispatch

### `backend/application/use_cases/text_chat.py`
- current business capability
- owns the text-chat flow

### `backend/application/services/input_normalizer.py`
- converts API payload into internal state
- later evolves to support multimodal input

### `backend/application/services/route_resolver.py`
- currently returns only `general_text`
- later becomes the decision point for routing

### `backend/application/services/prompt_factory.py`
- builds prompts
- later supports style-aware and route-aware prompt creation

### `backend/application/services/response_formatter.py`
- converts LangChain output into the backend response model

### `backend/chains/general_text_chain.py`
- contains the LCEL chain builder for the active route
- keeps chain composition separate from higher-level orchestration

### `backend/infrastructure/llm/model_selector.py`
- picks the model to use
- later supports model switching rules

### `backend/infrastructure/llm/anthropic_gateway.py`
- provider-specific LangChain model setup

### `backend/shared/settings.py`
- model names, timeouts, API base URLs, debug flags

### `backend/shared/exceptions.py`
- custom exceptions and mapping helpers

## 13. Example code shape

```python
# backend/orchestrator/assistant_orchestrator.py
class AssistantOrchestrator:
    def __init__(
        self,
        input_normalizer,
        route_resolver,
        text_chat_use_case,
        response_formatter,
    ) -> None:
        self.input_normalizer = input_normalizer
        self.route_resolver = route_resolver
        self.text_chat_use_case = text_chat_use_case
        self.response_formatter = response_formatter

    def execute(self, request):
        state = self.input_normalizer.normalize(request)
        route = self.route_resolver.resolve(state)

        if route == "general_text":
            raw_result = self.text_chat_use_case.execute(state)
        else:
            raise ValueError(f"Unsupported route: {route}")

        return self.response_formatter.format(raw_result)
```

```python
# backend/application/use_cases/text_chat.py
class TextChatUseCase:
    def __init__(self, prompt_factory, model_selector, chain_builder) -> None:
        self.prompt_factory = prompt_factory
        self.model_selector = model_selector
        self.chain_builder = chain_builder

    def execute(self, state):
        prompt = self.prompt_factory.build_general_text_prompt()
        model = self.model_selector.select_default_text_model()
        chain = self.chain_builder.build(prompt, model)
        return chain.invoke({"message": state.message})
```

## 14. Incremental extension plan

### Phase 1: working text-only MVP
- implement current architecture exactly as described

### Phase 2: structured output
- add `.with_structured_output()`
- extend `ResponseFormatter`

### Phase 3: user profiles
- add `ProfileProvider`
- enrich normalized state before route resolution
- update prompts with user-specific context

### Phase 4: weather tool
- add `WeatherUseCase`
- add `ToolRegistry`
- update `RouteResolver` to choose between `general_text` and `weather_text`

### Phase 5: conversation memory
- add `MemoryProvider`
- wrap the selected chain with `RunnableWithMessageHistory`

### Phase 6: image understanding
- extend `InputNormalizer` to accept image input
- add `ImageAnalysisUseCase`
- update `RouteResolver`
- update Streamlit UI to upload files

### Phase 7: dynamic style and model switching
- extend `PromptFactory` for style selection
- extend `ModelSelector` to choose by route and complexity

## 15. When this approach is ideal
Choose this if you want the code to stay easy to understand now, while still making room for the full assistant architecture to grow one feature at a time.

This is the best fit when:

- the project will definitely grow beyond text chat
- the team wants to avoid both over-engineering and future rewrites
- readability matters more than minimizing file count

## 16. Official sources consulted
- LangChain `RunnableWithMessageHistory`: https://python.langchain.com/api_reference/core/runnables/langchain_core.runnables.history
- LangChain `RunnableBranch`: https://python.langchain.com/api_reference/_modules/langchain_core/runnables/branch
- LangChain tools API: https://python.langchain.com/api_reference/core/tools
- FastAPI tutorial: https://fastapi.tiangolo.com/tutorial/
- Streamlit state and rerun behavior: https://docs.streamlit.io/develop/api-reference/caching-and-state
