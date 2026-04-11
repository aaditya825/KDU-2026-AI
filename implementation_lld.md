# Low-Level Design Document

## Overview

This document describes the current implementation of the context-aware multimodal AI assistant built with:

- `Streamlit` for the frontend
- `FastAPI` for the backend
- `LangChain LCEL` for prompt and model orchestration
- `Google Gemini` for text and image understanding

The application currently supports:

- general text chat
- context-aware weather responses
- structured JSON responses
- session-scoped memory
- image upload and image analysis
- frontend-controlled dynamic behavior using style, expertise, and response length

---

## Requirements Coverage

### 1. Context-Aware Responses
Implemented.

- Hidden `user_id` is used to load a user profile
- Weather location can be inferred from the stored profile
- Explicit location in the prompt overrides the profile location
- Real weather data is fetched from Open-Meteo

### 2. Structured Output
Implemented for active routes.

- `general_text` returns a structured answer
- `weather_text` returns:
  - `answer`
  - `location`
  - `temperature_c`
  - `summary`
- `image_text` returns:
  - `answer`
  - `description`
  - `objects`
  - `summary`

### 3. Memory Management
Implemented at MVP level.

- Session-based message history is stored in memory
- `RunnableWithMessageHistory` is used in the active chains
- Conversation history is scoped by `session_id`

### 4. Multimodal Image Processing
Implemented.

- Frontend supports image upload
- Backend validates and normalizes image input
- Gemini image analysis is routed through a dedicated image use case

### 5. Dynamic Behavior
Implemented.

- Frontend sends:
  - `communication_style`
  - `expertise_level`
  - `preferred_response_length`
- Backend middleware resolves effective behavior before route execution
- Route-aware defaults are applied when the frontend does not provide values

### 6. Model Switching
Not implemented as a true task-based model policy.

- The active model path uses Gemini
- Dynamic behavior is implemented, but model switching is still a future enhancement

---

## Architecture Diagram

```text
+-----------------------------------------------------------------------+
|                           STREAMLIT FRONTEND                           |
|                                                                       |
|  - Chat UI                                                            |
|  - User selection                                                     |
|  - Style / Expertise / Length controls                               |
|  - Prompt input and image upload                                      |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
|                           FASTAPI ROUTER                              |
|                                                                       |
|  - POST /assistant/chat                                               |
|  - GET /assistant/users                                               |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
|                        ASSISTANT ORCHESTRATOR                         |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
|                         INPUT NORMALIZER                              |
|                                                                       |
|  - Normalize text fields                                              |
|  - Decode and validate images                                         |
|  - Build internal request object                                      |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
|                          ROUTE RESOLVER                               |
|                                                                       |
|  - general_text                                                       |
|  - weather_text                                                       |
|  - image_text                                                         |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
|                  DYNAMIC BEHAVIOR MIDDLEWARE                          |
|                                                                       |
|  - Resolve effective style                                            |
|  - Resolve effective expertise                                        |
|  - Resolve effective response length                                  |
|  - Apply route-aware defaults                                         |
+-----------------------------------------------------------------------+
                                  |
                +-----------------+-----------------+
                |                 |                 |
                v                 v                 v
+--------------------------+ +--------------------------+ +--------------------------+
|      TEXT USE CASE       | |     WEATHER USE CASE    | |      IMAGE USE CASE      |
+--------------------------+ +--------------------------+ +--------------------------+
                |                 |                 |
                v                 v                 v
+--------------------------+ +--------------------------+ +--------------------------+
|   GENERAL TEXT CHAIN     | | WEATHER TOOL CALL FLOW  | |      IMAGE CHAIN         |
+--------------------------+ +--------------------------+ +--------------------------+
                |                 |                 |
                |                 v                 |
                |      +----------------------+     |
                |      |  WEATHER TOOL        |     |
                |      |  get_current_weather |     |
                |      +----------------------+     |
                |                 |                 |
                |                 v                 |
                |      +----------------------+     |
                |      |  WEATHER SERVICE      |    |
                |      | (Open-Meteo APIs)     |    |
                |      +----------------------+     |
                |                                   |
                +--------+---------------+----------+
                         |               |
                         v               v
              +-------------------+   +----------------------+
              |   PROMPT FACTORY  |   |  MESSAGE HISTORY     |
              |                   |   |  STORE / MEMORY      |
              +-------------------+   +----------------------+
                         |
                         v
              +-------------------+
              |   MODEL SELECTOR  |
              |      (Gemini)     |
              +-------------------+
                         |
                         v
              +-------------------+
              |    GEMINI API      |
              +-------------------+

Final response path:

Use Case Result --> Response Formatter --> FastAPI Router --> Streamlit UI
```

---

## Layered Architecture Breakdown

### 1. UI Layer
Responsible for:

- rendering the chat UI
- collecting prompt, image, and behavior inputs
- sending requests to the backend
- rendering responses and errors

Main files:

- [streamlit_app.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\frontend\streamlit_app.py)
- [chat_page.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\frontend\ui\chat_page.py)
- [api_client.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\frontend\api_client.py)

### 2. API / Controller Layer
Responsible for:

- receiving HTTP requests
- validating request contracts
- returning typed responses

Main files:

- [main.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\main.py)
- [assistant.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\api\routers\assistant.py)
- [dependencies.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\api\dependencies.py)

### 3. Orchestration Layer
Responsible for:

- coordinating the full request flow
- applying route selection
- invoking the correct use case
- formatting the final response

Main file:

- [assistant_orchestrator.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\orchestrator\assistant_orchestrator.py)

### 4. Middleware / Policy Layer
Responsible for:

- resolving dynamic behavior before the use-case layer runs
- applying route-aware defaults
- normalizing invalid frontend behavior values

Main file:

- [dynamic_behavior_middleware.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\application\services\dynamic_behavior_middleware.py)

### 5. Use Case Layer
Responsible for implementing feature-specific business flows.

Main files:

- [text_chat.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\application\use_cases\text_chat.py)
- [weather_chat.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\application\use_cases\weather_chat.py)
- [image_chat.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\application\use_cases\image_chat.py)

### 6. LangChain / Infrastructure Layer
Responsible for:

- building prompts
- building LCEL chains
- integrating with Gemini
- storing message history
- integrating tool-calling and external weather APIs

Main files:

- [prompt_factory.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\application\services\prompt_factory.py)
- [general_text_chain.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\chains\general_text_chain.py)
- [weather_text_chain.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\chains\weather_text_chain.py)
- [image_text_chain.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\chains\image_text_chain.py)
- [model_selector.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\infrastructure\llm\model_selector.py)
- [message_history_store.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\application\services\message_history_store.py)
- [weather_service.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\application\services\weather_service.py)
- [weather_tool_provider.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\application\services\weather_tool_provider.py)
- [weather_tool_caller.py](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\backend\application\services\weather_tool_caller.py)

---

## End-to-End Request Flows

### 1. General Text Flow

1. User enters a prompt in Streamlit
2. Frontend sends the request to `POST /assistant/chat`
3. Backend normalizes the request
4. Route resolver selects `general_text`
5. Dynamic behavior middleware resolves effective style, expertise, and response length
6. `TextChatUseCase` builds the payload for the general text LCEL chain
7. LangChain prompt + Gemini model are invoked
8. Structured result is formatted into `AssistantResponse`
9. Frontend renders the assistant response

### 2. Weather Flow

1. User asks a weather-related question
2. Backend normalizes the request
3. Route resolver selects `weather_text`
4. Dynamic behavior middleware resolves the final behavior settings
5. `WeatherChatUseCase` loads the user profile
6. The use case extracts location from the prompt, or falls back to the profile location
7. A dedicated weather tool-calling flow asks Gemini to call `get_current_weather`
8. The weather tool executes the backend weather service against Open-Meteo
9. The returned weather data is passed into the structured weather chain
10. Structured response is returned and rendered in the UI

### 3. Image Analysis Flow

1. User uploads an image and optionally adds a prompt
2. Frontend sends the image as base64 with MIME type
3. Backend normalizes and validates the image
4. Route resolver selects `image_text`
5. Dynamic behavior middleware resolves the final behavior settings
6. `ImageChatUseCase` builds a multimodal `HumanMessage`
7. Gemini processes the text + image input
8. Structured image analysis is returned
9. Frontend renders the request image preview and the assistant analysis

---

## Component Breakdown

### Streamlit UI
Collects:

- prompt text
- optional image
- style
- expertise
- response length
- selected user

It also renders:

- chat history
- image previews
- weather details
- image-analysis details

### FastAPI Router
Defines:

- `POST /assistant/chat`
- `GET /assistant/users`

This layer stays thin and delegates to the orchestrator.

### Assistant Orchestrator
This is the backend entry point for the business flow.

It:

- normalizes input
- resolves route
- applies dynamic behavior middleware
- runs the correct use case
- formats the final response

### Dynamic Behavior Middleware
This is an application-layer middleware/policy service.

It:

- resolves the final request behavior
- applies route defaults
- preserves explicit frontend choices
- keeps dynamic behavior logic out of the use cases

### Route Resolver
Chooses the active route:

- `image_text` if image is present
- `weather_text` for weather-related prompts
- `general_text` otherwise

### Prompt Factory
Builds route-specific prompt instructions.

It includes:

- behavior instructions
- guardrails
- schema-alignment instructions
- normalized style/expertise/length instructions

### User Profile Store
Stores hidden user context for:

- `user_id`
- `name`
- `location`

It is currently an in-memory store.

### Weather Service
Calls Open-Meteo for:

- geocoding
- current weather data

This is the backend implementation behind the explicit weather tool.

### Weather Tool Provider
Exposes `get_current_weather` as a LangChain tool.

This allows the weather path to use explicit tool calling instead of directly calling the service from the use case.

### Weather Tool Caller
Runs the model-driven weather tool flow.

It:

- prompts Gemini to call the weather tool
- executes the tool call
- converts the tool result into a typed weather snapshot
- passes the weather data forward into the weather response chain

### Message History Store
Stores short-term conversation history by `session_id`.

This is used by `RunnableWithMessageHistory`.

### Model Selector
Creates the active Gemini chat model and applies structured output wrappers when needed.

---

## Folder Structure

```text
docs/
  implementation_lld.md
  requirement_alignment.md
  mvp_approaches/

src/
  assistant/
    backend/
      api/
      application/
        services/
        use_cases/
      chains/
      contracts/
      infrastructure/
      orchestrator/
      shared/
    frontend/
      ui/

tests/
  integration/
  unit/
```

### Folder Explanation

- `backend/api/`: FastAPI routers and dependency wiring
- `backend/application/services/`: reusable backend services and policy/middleware logic
- `backend/application/use_cases/`: feature-specific business flows
- `backend/chains/`: LangChain LCEL chain builders
- `backend/contracts/`: request and response schemas
- `backend/infrastructure/`: model/provider integration
- `backend/orchestrator/`: top-level backend coordination
- `backend/shared/`: settings and shared exceptions
- `frontend/ui/`: Streamlit page rendering
- `tests/unit/`: component-level tests
- `tests/integration/`: API-level tests

---

## Key Design Decisions

### 1. Service-Layer Orchestration
The backend uses an explicit orchestrator and use-case structure instead of a single large LangChain agent.

Why:

- easier to test
- easier to debug
- clearer separation of concerns

### 2. Weather as Explicit Tool Calling
Weather lookup is implemented through an explicit LangChain tool-calling flow.

Why:

- it satisfies the tool-usage requirement more directly
- the model explicitly requests weather data through a tool call
- the actual data fetch still remains deterministic because the tool executes backend code against Open-Meteo
- it preserves clear separation between data retrieval and response generation

### 3. Dynamic Behavior as Application Middleware
Dynamic behavior is implemented as an application-layer middleware, not as FastAPI HTTP middleware.

Why:

- behavior resolution is part of request-processing logic, not transport logic
- it fits naturally between route resolution and use-case execution
- use cases stay simple because they receive already-resolved behavior

### 4. In-Memory Memory Store
Short-term memory is stored in memory and keyed by `session_id`.

Why:

- simple MVP implementation
- enough to demonstrate `RunnableWithMessageHistory`
- easy to replace with persistent storage later

### 5. Gemini as the Active Model Path
The active model provider is Gemini.

Why:

- one provider path keeps the implementation simple
- Gemini supports both text and image analysis
- it matches the current multimodal requirements well

### 6. Frontend-Controlled Behavior Settings
Style, expertise, and response length are selected in the frontend and passed to the backend.

Why:

- avoids hardcoding behavior preferences in the backend profile
- makes the dynamic behavior directly visible to the user
- keeps hidden profile context limited to identity and location

---

## Current Limitations

- model switching is not implemented as a real policy
- memory is still in-memory only
- long multi-turn memory behavior is not deeply validated with the live provider
- user profiles are not persisted in a database
- image preview expansion opens in a new tab instead of an in-app lightbox
- live weather tool-calling with Gemini is still sensitive to the current environment's DNS/connectivity issues

---

## Future Enhancements

- add true task-based model switching
- replace in-memory memory with persistent storage
- add persistent profile storage
- add broader tool orchestration if needed
- improve frontend image preview with an in-app modal or lightbox
- strengthen runtime guardrails for response quality and safety
