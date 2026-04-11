# Low-Level Design: MVP Approach 3 - Extension-Ready LCEL Skeleton

## 1. Goal of this MVP
Implement only one real feature now, text-only chat, while shaping the backend around the architecture you ultimately want:

- orchestrator
- chain builder
- router stub
- tool registry stub
- memory abstraction
- frontend and API contracts already aligned with future multimodal growth

Only the `general_text` path is active in this MVP. The other pieces exist mainly as extension points.

## 2. Why choose this approach
This approach is useful if you are already confident that the final solution will include:

- tool use
- memory
- multimodal inputs
- dynamic routing
- multiple model strategies

Instead of refactoring later, you create the skeleton once and fill features in one by one.

## 3. Architecture

```text
Streamlit UI
    |
    v
FastAPI /assistant/chat
    |
    v
Assistant Orchestrator
    |
    v
Input Normalizer
    |
    v
Router Stub ----------------------------- future weather/image branches
    |
    v
General Text Chain Builder
    |
    v
Prompt Factory -> Model Selector -> Structured Output
    |
    v
Response Envelope
```

Future components are present but inactive:

- `ToolRegistry`
- `MemoryProvider`
- `UserProfileProvider`
- `ImageInputNormalizer`

## 4. Core components

### 4.1 Streamlit Frontend
Responsibilities:

- capture input
- call backend
- render response
- later support file upload without redesigning the whole page

### 4.2 FastAPI Assistant Router
Responsibilities:

- expose one stable endpoint
- keep transport concerns outside orchestration logic

### 4.3 AssistantOrchestrator
Responsibilities:

- entry point for the backend
- normalize state
- call the router
- return a stable response envelope

### 4.4 InputNormalizer
Responsibilities:

- normalize current request into a consistent state dictionary or request object
- right now handle only text
- later support image payloads and hidden profile identifiers

### 4.5 Router Stub
Responsibilities:

- currently always route to `general_text`
- later switch to `RunnableBranch` or equivalent conditional routing

### 4.6 GeneralTextChainBuilder
Responsibilities:

- build the single working LCEL chain for this MVP

### 4.7 PromptFactory
Responsibilities:

- create reusable prompts
- later branch by style or task

### 4.8 ModelSelector
Responsibilities:

- return the default model for now
- later switch based on task complexity

### 4.9 OutputFormatter
Responsibilities:

- keep final response stable
- later enforce strict route-specific schemas

## 5. How the current MVP works

1. Streamlit sends a text request.
2. FastAPI validates the request.
3. `AssistantOrchestrator` creates a normalized state.
4. `RouterStub` returns `general_text`.
5. `GeneralTextChainBuilder` supplies `prompt | model`.
6. The chain runs through LangChain.
7. The output formatter returns a stable response object.
8. Streamlit renders the result.

## 6. How this differs from Approach 2
Approach 2 adds only abstractions that are immediately useful. Approach 3 adds some abstractions before they are needed because it is optimizing for future feature insertion.

That means:

- cleaner future migrations
- slightly more conceptual overhead now

## 7. LangChain usage in this MVP
The active path uses:

- `ChatPromptTemplate`
- one chat model
- `RunnableLambda` if needed for input-state shaping
- pipe composition
- `.invoke()`

The skeleton reserves space for:

- `RunnableBranch`
- `RunnableWithMessageHistory`
- `.bind_tools()`
- `.with_structured_output()`

## 8. Pros
- closest to the final target architecture
- easiest future insertion point for weather, memory, and multimodal support
- orchestrator concept is introduced early

## 9. Cons
- more files before they are truly needed
- beginners may find “empty future hooks” a bit abstract
- higher chance of premature architecture if requirements change

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
        request_models.py
        response_models.py
      orchestrator/
        assistant_orchestrator.py
      chains/
        general_text_chain.py
        builders.py
      routing/
        router_stub.py
      prompts/
        prompt_factory.py
      llm/
        model_selector.py
      tools/
        registry.py
      memory/
        provider.py
      profiles/
        provider.py
      input/
        normalizer.py
      output/
        formatter.py
      shared/
        settings.py
        constants.py
```

## 11. Module-by-module explanation

### `contracts/request_models.py`
- request and response schemas shared across backend layers

### `orchestrator/assistant_orchestrator.py`
- main application entry point
- central place where all parts meet

### `chains/general_text_chain.py`
- only working chain in this MVP

### `routing/router_stub.py`
- currently returns one route
- later becomes the real router

### `tools/registry.py`
- empty or minimal now
- future home for weather and image tools

### `memory/provider.py`
- interface placeholder for future `RunnableWithMessageHistory` integration

### `profiles/provider.py`
- placeholder for future user profile loading

### `input/normalizer.py`
- good place to add text-plus-image normalization later

### `output/formatter.py`
- stable response mapping layer

## 12. Example code shape

```python
# orchestrator/assistant_orchestrator.py
class AssistantOrchestrator:
    def __init__(self, input_normalizer, router, chain_builder, formatter) -> None:
        self.input_normalizer = input_normalizer
        self.router = router
        self.chain_builder = chain_builder
        self.formatter = formatter

    def execute(self, request):
        state = self.input_normalizer.normalize(request)
        route = self.router.select(state)
        chain = self.chain_builder.build(route)
        raw_result = chain.invoke(state)
        return self.formatter.format(raw_result)
```

## 13. Future extension path

### Add user profiles
- implement `profiles/provider.py`
- inject profile into normalized state

### Add weather
- add `weather_chain.py`
- add weather tool
- update router to choose between `general_text` and `weather_text`

### Add memory
- implement `memory/provider.py`
- wrap the chosen chain with `RunnableWithMessageHistory`

### Add image support
- extend `input/normalizer.py`
- add `image_chain.py`
- update API and Streamlit UI to accept files

### Add style/model switching
- expand `model_selector.py`
- expand `prompt_factory.py`
- extend router decision object

## 14. When this approach is ideal
Choose this if you already know the project will become a real multi-feature assistant and you want the codebase shape to stay stable while features are added one by one.

## 15. Official sources consulted
- LangChain `RunnableWithMessageHistory`: https://python.langchain.com/api_reference/core/runnables/langchain_core.runnables.history
- LangChain `RunnableBranch`: https://python.langchain.com/api_reference/_modules/langchain_core/runnables/branch
- FastAPI tutorial: https://fastapi.tiangolo.com/tutorial/
- Streamlit state and rerun behavior: https://docs.streamlit.io/develop/api-reference/caching-and-state
