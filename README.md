# Stock Trading Agent

This project is a Streamlit app backed by a LangGraph workflow for:
- portfolio valuation
- stock trade requests with human approval
- currency conversion (USD/INR/EUR)

## Architecture (SOLID-Oriented)

The codebase now follows a layered structure with dependency inversion and clear responsibilities:

```text
src/
  trading_agent/
    domain/            # State, value objects, interfaces (protocols)
    application/       # Use-case services (intent, portfolio, trade)
    infrastructure/    # Gemini parser, stock simulator, currency service, checkpointer
    orchestration/     # LangGraph nodes, routes, graph assembly/invocation
    bootstrap/         # Dependency composition root

  agent/               # Compatibility facades (legacy imports)
  tools/               # Compatibility facades for old utility module paths
  ui/                  # Streamlit UI
  utils/               # Cross-cutting concerns (logging/session)
```

## Why this is easier to extend

- Single Responsibility: parsing, pricing, trading, persistence, and routing are isolated.
- Open/Closed: add new behavior by creating new service implementations, not by editing all nodes.
- Liskov + Interface Segregation: protocols in `domain/interfaces.py` keep contracts small and swappable.
- Dependency Inversion: application services depend on interfaces; concrete dependencies are wired in `bootstrap/container.py`.

## Add new functionality

1. Add/extend interface in `src/trading_agent/domain/interfaces.py` (if needed).
2. Add implementation in `src/trading_agent/infrastructure/...`.
3. Add/extend use-case service in `src/trading_agent/application/services/...`.
4. Wire dependencies in `src/trading_agent/bootstrap/container.py`.
5. Expose behavior through orchestration node/route in `src/trading_agent/orchestration/...`.

## Run Backend

Start FastAPI backend first:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn src.backend.app:app --reload --host 127.0.0.1 --port 8000
```

## Run Frontend

In a second terminal:

```powershell
.\venv\Scripts\Activate.ps1
streamlit run src/app.py
```

Optional:
- Set `BACKEND_URL` if backend is not at `http://127.0.0.1:8000`.
