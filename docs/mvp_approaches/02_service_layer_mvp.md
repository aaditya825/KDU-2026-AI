# Low-Level Design: MVP Approach 2 - Clean Service-Layer MVP

## 1. Goal of this MVP
Build a text-only assistant first, but structure the code so later features can be added without major rewrites.

This MVP implements:

- Streamlit frontend
- FastAPI backend
- one text-only LangChain flow
- structured response
- clear service boundaries

This MVP still does **not** implement:

- image input
- tools
- message history
- routing between multiple branches

## 2. Why this is the recommended starting point
This approach is the best balance between simplicity and maintainability.

It respects SOLID in a practical way:

- Single Responsibility: API, service, prompt building, and model access are separated
- Open/Closed: new services or flows can be added without rewriting the controller
- Liskov Substitution: model gateway implementations can be swapped
- Interface Segregation: the frontend does not know LangChain details
- Dependency Inversion: the service depends on abstractions such as a model gateway, not a concrete provider

It is still easy for a beginner to follow because there is only one implemented use case: `text_chat`.

## 3. Architecture

```text
Streamlit UI
    |
    v
FastAPI Router
    |
    v
TextChatUseCase
    |----------------------|
    v                      v
PromptBuilder         LLMGateway
    |                      |
    ----------LCEL Chain----
              |
              v
Structured Response Mapper
              |
              v
FastAPI JSON Response
```

## 4. Core components

### 4.1 Streamlit Client
Responsibilities:

- capture user text
- call FastAPI
- render typed response
- keep lightweight UI state in `st.session_state`

### 4.2 FastAPI Router
Responsibilities:

- expose `/chat`
- validate request schema
- call the use case
- convert exceptions to HTTP responses

### 4.3 TextChatUseCase
Responsibilities:

- coordinate prompt builder and LLM gateway
- own the single business operation
- hide LangChain from the API layer

### 4.4 PromptBuilder
Responsibilities:

- build system and human messages
- control tone and output instructions
- remain independent from provider logic

### 4.5 LLMGateway
Responsibilities:

- build or return the LangChain chat model
- hide provider-specific configuration

### 4.6 ResponseMapper
Responsibilities:

- convert model output into the API response schema
- optionally enforce structured output

## 5. How the solution works

1. Streamlit sends a chat request.
2. FastAPI validates it using `ChatRequest`.
3. The router calls `TextChatUseCase`.
4. The use case gets a prompt from `PromptBuilder`.
5. The use case gets a model from `LLMGateway`.
6. The use case invokes the LCEL chain.
7. The response mapper converts the result into `ChatResponse`.
8. FastAPI returns JSON.
9. Streamlit renders the fields.

## 6. LangChain usage in this MVP
This approach uses LangChain more intentionally than Approach 1:

- `ChatPromptTemplate` for prompt construction
- `Runnable` composition with the pipe operator
- `.invoke()` for execution
- optional `.with_structured_output()` for stable JSON

Still intentionally deferred:

- `RunnableBranch`
- `RunnableWithMessageHistory`
- `.bind_tools()`

## 7. Pros
- clean and easy to read
- much better extension path than the vertical slice
- SOLID-friendly without being over-engineered
- easiest approach to test properly

## 8. Cons
- slower to implement than Approach 1
- introduces abstractions before they are strictly required

## 9. Ideal folder structure

```text
src/
  assistant/
    frontend/
      streamlit_app.py
    backend/
      main.py
      api/
        routers/
          chat.py
      domain/
        models/
          chat_request.py
          chat_response.py
      application/
        use_cases/
          text_chat.py
        services/
          prompt_builder.py
          response_mapper.py
      infrastructure/
        llm/
          gateway.py
          anthropic_gateway.py
      shared/
        settings.py
        exceptions.py
```

## 10. Module-by-module explanation

### `frontend/streamlit_app.py`
- UI only
- should not contain prompt logic or LangChain code

### `backend/api/routers/chat.py`
- HTTP boundary only
- receives `ChatRequest`
- returns `ChatResponse`

### `backend/domain/models/chat_request.py`
- input schema

### `backend/domain/models/chat_response.py`
- output schema

### `backend/application/use_cases/text_chat.py`
- the main business entry point
- orchestrates the current MVP flow

### `backend/application/services/prompt_builder.py`
- builds the prompt
- future home for personalization and style modes

### `backend/application/services/response_mapper.py`
- isolates output formatting logic
- future home for structured-output parsing

### `backend/infrastructure/llm/gateway.py`
- defines the model access abstraction

### `backend/infrastructure/llm/anthropic_gateway.py`
- concrete implementation for Anthropic through LangChain

### `backend/shared/settings.py`
- model names, API URLs, timeouts, debug flags

## 11. Example code shape

```python
# application/use_cases/text_chat.py
class TextChatUseCase:
    def __init__(self, prompt_builder, llm_gateway, response_mapper) -> None:
        self.prompt_builder = prompt_builder
        self.llm_gateway = llm_gateway
        self.response_mapper = response_mapper

    def execute(self, message: str):
        prompt = self.prompt_builder.build_text_chat_prompt()
        model = self.llm_gateway.get_chat_model()
        chain = prompt | model
        raw = chain.invoke({"message": message})
        return self.response_mapper.to_chat_response(raw)
```

## 12. Future extension path

### Add personalization
- add `UserProfileRepository`
- inject profile into `TextChatUseCase`
- extend `PromptBuilder`

### Add weather
- introduce `WeatherUseCase`
- add `WeatherTool`
- later add a router that chooses between `TextChatUseCase` and `WeatherUseCase`

### Add memory
- create `MemoryService`
- wrap the chain in `RunnableWithMessageHistory`

### Add multimodal
- add `InputHandler`
- add image-aware prompt builder
- create `ImageAnalysisUseCase`

### Add model switching
- extend `LLMGateway` to select models by task type

## 13. When this approach is ideal
Choose this if you want the easiest codebase to grow over several milestones without introducing future-facing abstractions too early.

## 14. Official sources consulted
- FastAPI tutorial: https://fastapi.tiangolo.com/tutorial/
- Streamlit state and rerun behavior: https://docs.streamlit.io/develop/api-reference/caching-and-state
- LangChain chat prompt and runnable patterns: https://python.langchain.com/
