# Demo UI

This folder contains a separate Streamlit UI for showcasing the backend flows directly.

## What It Demonstrates
- health and version endpoints
- user registration
- login
- refresh token rotation
- current user lookup
- admin-only user listing
- request and response logging inside the UI

## Run The Backend
From the repo root:

```bash
make run
```

Backend default target:

```text
http://127.0.0.1:8000/api/v1
```

## Run The Streamlit UI
From the repo root:

```bash
streamlit run demo-ui/streamlit_app.py
```

Then open the local Streamlit URL shown in the terminal, typically:

```text
http://localhost:8501
```

## Notes
- The UI stores access and refresh tokens in Streamlit session state for demo convenience.
- This UI is not part of the backend runtime. It is only a showcase layer.
- If your backend runs on a different host or port, update the API base URL in the Streamlit sidebar.
