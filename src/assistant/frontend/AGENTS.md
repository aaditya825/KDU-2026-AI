# Frontend Guidance

This file applies to `src/assistant/frontend/`.

## Frontend responsibilities
The Streamlit frontend owns:

- user interaction
- rendering
- short-lived UI state
- backend API calls

The frontend does not own:

- LangChain chains
- prompt design
- business rules
- provider-specific LLM logic

## Implementation rules

- Keep the Streamlit app thin.
- Route all assistant behavior through the FastAPI backend.
- Store only UI state in `st.session_state`.
- Keep API access in a small client helper instead of scattering HTTP calls.
- Render typed backend responses; do not infer business meaning from raw model strings in the UI.

## UI phase plan

### Phase 1
- one text input area
- submit action
- assistant response rendering
- loading and error states

### Phase 2
- conversation view
- response metadata display if useful

### Phase 3
- file uploader for image input

## Guardrails

- no direct model calls from Streamlit
- no secret handling in frontend code
- no backend contract drift; update frontend if request or response schemas change

## Preferred structure

```text
frontend/
  streamlit_app.py
  api_client.py
  ui/
    chat_page.py
    components.py
```

Keep this small until the UI actually needs more decomposition.
