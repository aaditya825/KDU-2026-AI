# Low-Level Design: MVP Approach 1 - Ultra-Simple Vertical Slice

## 1. Goal of this MVP
Build the smallest possible version of the assistant that proves the end-to-end product works:

- user types text in Streamlit
- Streamlit sends request to FastAPI
- FastAPI calls a LangChain text chain
- model returns a structured response
- Streamlit renders the answer

This MVP does **not** include:

- image input
- tools
- memory
- routing
- user profiles

It intentionally solves only one problem well: **basic text chat**.

## 2. Why start here
This is the best architecture if the team wants immediate momentum. It proves the frontend, backend, model connectivity, environment management, and request-response contract before adding complexity.

This approach is especially useful because Streamlit reruns the script on user interaction, FastAPI prefers explicit request/response schemas, and LangChain works best when introduced one primitive at a time. The first slice should therefore stay extremely thin.

## 3. Architecture

```text
Streamlit UI
    |
    v
POST /chat
    |
    v
FastAPI Chat Controller
    |
    v
Chat Service
    |
    v
LangChain Prompt -> Chat Model -> Structured Output
    |
    v
FastAPI Response Model
    |
    v
Streamlit Render
```

## 4. Core components

### 4.1 Streamlit Frontend
Purpose:

- capture text input
- call the backend
- display the assistant response

Responsibilities:

- render one text input area and submit button
- call FastAPI using HTTP
- display structured response fields
- optionally keep the latest response in `st.session_state`

### 4.2 FastAPI Chat Endpoint
Purpose:

- expose the backend API

Responsibilities:

- validate request body
- call application service
- return typed response

### 4.3 Chat Service
Purpose:

- own the single business use case: generate a text answer

Responsibilities:

- accept normalized input text
- build prompt variables
- invoke the LangChain chain
- return a typed response object

### 4.4 Prompt Builder
Purpose:

- keep prompt text outside the API route

Responsibilities:

- build a very small `ChatPromptTemplate`
- inject user text into the prompt
- optionally include one stable system message

### 4.5 Model Gateway
Purpose:

- hide provider-specific LangChain model initialization

Responsibilities:

- initialize the chat model
- expose a simple `invoke()`-compatible runnable

### 4.6 Output Schema
Purpose:

- make the API response predictable from day one

Responsibilities:

- define one simple Pydantic response model
- keep frontend rendering stable

## 5. How it works step by step

1. User types a message in Streamlit.
2. Streamlit sends `POST /chat` with `{ "message": "..." }`.
3. FastAPI validates the payload with a Pydantic request model.
4. The chat service builds a prompt using `ChatPromptTemplate`.
5. The LangChain model is invoked.
6. The response is parsed into a small typed output model.
7. FastAPI returns JSON to Streamlit.
8. Streamlit renders the answer.

## 6. LangChain usage in this MVP
Use only the minimum necessary primitives:

- `ChatPromptTemplate`
- one chat model such as `ChatOpenAI` or `ChatAnthropic`
- `.invoke()`
- optionally `.with_structured_output()` if you want structured JSON from the start

Avoid in this MVP:

- `RunnableBranch`
- `RunnableWithMessageHistory`
- `bind_tools`
- custom routers

## 7. Pros
- fastest to implement
- easiest to explain
- minimal debugging surface
- ideal for validating environment setup and deployment path

## 8. Cons
- not very future-ready
- adding tools or memory will require refactoring
- no natural place yet for multimodal logic

## 9. Ideal folder structure

```text
src/
  app/
    frontend/
      streamlit_app.py
    backend/
      main.py
      api/
        chat.py
      schemas/
        chat_request.py
        chat_response.py
      services/
        chat_service.py
      llm/
        model_factory.py
      prompts/
        chat_prompt.py
```

## 10. Module-by-module explanation

### `frontend/streamlit_app.py`
- contains the Streamlit page
- collects text input
- sends the request to FastAPI
- renders returned JSON

### `backend/main.py`
- creates the FastAPI app
- includes routers

### `backend/api/chat.py`
- defines `/chat`
- should contain almost no business logic

### `backend/schemas/chat_request.py`
- defines the incoming request model

### `backend/schemas/chat_response.py`
- defines the API response model

### `backend/services/chat_service.py`
- holds the core use-case logic
- should be the first place to test

### `backend/llm/model_factory.py`
- initializes the LangChain chat model

### `backend/prompts/chat_prompt.py`
- holds the prompt builder function

## 11. Example code shape

```python
# backend/services/chat_service.py
from app.backend.prompts.chat_prompt import build_prompt
from app.backend.llm.model_factory import build_model


class ChatService:
    def __init__(self) -> None:
        self.model = build_model()
        self.prompt = build_prompt()
        self.chain = self.prompt | self.model

    def generate(self, message: str) -> str:
        result = self.chain.invoke({"message": message})
        return result.content if hasattr(result, "content") else str(result)
```

## 12. How to extend this later

### Add structured output
- replace raw string response with `.with_structured_output()`

### Add personalization
- inject `user_id` and load a user profile before calling the chain

### Add weather
- add a weather service and narrow weather-only branch later

### Add memory
- wrap the chain with `RunnableWithMessageHistory`

### Add multimodal
- update the request contract to optionally include image content
- add a separate input handler module

## 13. Best use case for this approach
Choose this if the team needs a first success quickly and is comfortable refactoring after the first milestone.

## 14. Official sources consulted
- FastAPI tutorial: https://fastapi.tiangolo.com/tutorial/
- Streamlit state and rerun behavior: https://docs.streamlit.io/develop/api-reference/caching-and-state
- LangChain prompt and runnable patterns: https://python.langchain.com/
