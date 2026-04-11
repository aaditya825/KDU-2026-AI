---
name: "streamlit-chat-frontend"
description: "Use when implementing or modifying the Streamlit frontend for this assistant, including the chat page, UI state, API client behavior, request submission, and rendering of backend responses."
---

# Streamlit Chat Frontend

Use this skill for frontend work under `src/assistant/frontend/`.

## Read first
- [AGENTS.md](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\AGENTS.md)
- [src/assistant/frontend/AGENTS.md](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\src\assistant\frontend\AGENTS.md)
- [04_hybrid_service_lcel_mvp.md](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\docs\mvp_approaches\04_hybrid_service_lcel_mvp.md)

## Use this skill when
- building the first Streamlit page
- adding UI components for chat
- integrating the frontend with FastAPI
- adding loading, error, and empty states
- later adding file upload for multimodal input

## Frontend workflow

1. Start from the backend contract.
   - mirror request and response fields intentionally

2. Keep UI code thin.
   - collect input
   - call backend
   - render output

3. Use `st.session_state` only for UI state.
   - chat transcript display
   - current input value
   - loading or submission flags

4. Isolate HTTP calls.
   - keep backend request logic in a small helper module

## Guardrails

- no LangChain code in the frontend
- no direct model API calls from Streamlit
- no backend business logic duplicated in UI code
- do not guess response structure; use the backend contract

## Future extension notes

- when file upload lands, extend the API client first, then the UI
- keep one page until a second UI workflow actually exists
