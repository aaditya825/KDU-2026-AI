# Simplified Modular Code Structure

## Goal

From `docs/requirements.pdf`, the system must support:

- LangGraph-based multi-step workflow
- stateful execution
- conditional routing
- mock tool usage for stock prices and currency conversion
- checkpoint-based memory persistence
- human approval before sensitive trades
- LangSmith tracing
- token/cost tracking
- evaluation

So the structure should be simple, but it still needs clear separation of concerns.

## Recommended Structure

```text
KDU-2026-AI/
├── docs/
│   ├── requirements.pdf
│   └── modular_code_structure.md
├── data/
│   └── checkpoints.db
├── evaluation/
│   ├── run_eval.py
│   ├── datasets.py
│   └── metrics.py
├── src/
│   └── trading_agent/
│       ├── domain/
│       │   ├── models.py
│       │   ├── state.py
│       │   └── interfaces.py
│       ├── services/
│       │   ├── intent_service.py
│       │   ├── portfolio_service.py
│       │   ├── trade_service.py
│       │   └── observability_service.py
│       ├── orchestration/
│       │   ├── graph.py
│       │   ├── nodes.py
│       │   └── routes.py
│       ├── infrastructure/
│       │   ├── intent_parser.py
│       │   ├── stock_price_provider.py
│       │   ├── currency_converter.py
│       │   ├── checkpointer.py
│       │   └── langsmith_client.py
│       ├── api/
│       │   ├── app.py
│       │   ├── schemas.py
│       │   └── service.py
│       ├── ui/
│       │   ├── streamlit_app.py
│       │   ├── components.py
│       │   └── backend_client.py
│       ├── bootstrap/
│       │   └── container.py
│       └── __init__.py
├── tests/
│   ├── test_services.py
│   ├── test_graph.py
│   ├── test_api.py
│   └── test_evaluation.py
└── pyproject.toml
```

## What Each Part Does

### `domain/`

Core business definitions only.

- `models.py`: intent result, trade request, approval data
- `state.py`: shared LangGraph state
- `interfaces.py`: contracts for parser, price provider, currency converter

This layer should stay framework-independent.

### `services/`

Business logic of the app.

- `intent_service.py`: understands what the user wants
- `portfolio_service.py`: fetches prices, calculates value, converts currency
- `trade_service.py`: handles approval and executes buy/sell
- `observability_service.py`: records trace metadata, token usage, and cost summaries

This is the main logic layer.

### `orchestration/`

LangGraph-specific flow control.

- `graph.py`: builds and compiles the workflow
- `nodes.py`: thin node wrappers that call services
- `routes.py`: conditional routing decisions

This keeps LangGraph details separate from business logic.

### `infrastructure/`

Concrete external integrations.

- `intent_parser.py`: Gemini or other LLM-based intent parsing
- `stock_price_provider.py`: mock stock API
- `currency_converter.py`: static/mock currency conversion
- `checkpointer.py`: SQLite or memory checkpointing
- `langsmith_client.py`: LangSmith tracing integration

### `api/`

FastAPI backend.

- `app.py`: API entry point
- `schemas.py`: request/response models
- `service.py`: bridges API requests to the graph

### `ui/`

Streamlit frontend.

- `streamlit_app.py`: main UI app
- `components.py`: reusable UI pieces
- `backend_client.py`: talks to FastAPI

### `bootstrap/`

Dependency wiring.

- `container.py`: creates services and injects infrastructure dependencies

## Dependency Direction

Keep dependencies flowing like this:

```text
ui/api -> orchestration -> services -> domain
infrastructure -> domain
bootstrap -> everything
evaluation -> services/orchestration
```

Avoid this:

- `domain` importing LangGraph, FastAPI, Streamlit, or LangSmith
- `services` importing UI code
- `routes.py` containing business calculations
- API code directly using infrastructure instead of services

## SOLID in a Simple Way

### Single Responsibility

Each file should have one clear job.

Examples:

- `portfolio_service.py` should not also parse user intent
- `routes.py` should not execute trades
- `checkpointer.py` should not contain business rules

### Open/Closed

You should be able to swap implementations without rewriting the workflow.

Examples:

- replace mock stock provider with a real API later
- replace static currency converter with live rates
- replace Gemini parser with another LLM

### Interface Segregation and Dependency Inversion

Keep interfaces small and inject them into services.

Examples:

- `IntentParser`
- `StockPriceProvider`
- `CurrencyService`

Services should depend on these interfaces, not concrete classes.

## Suggested State Shape

Keep the state flat enough for LangGraph, but not messy.

```python
class PortfolioState(TypedDict):
    holdings: dict[str, int]
    messages: list
    current_step: str
    total_value: float | None
    currency: str
    stock_prices: dict[str, float]
    pending_trade: dict | None
    requires_approval: bool
    approval_granted: bool | None
    thread_id: str
    value_history: list[dict]
```

This is enough for the assignment without introducing too many nested models.

## Suggested Test Split

Keep testing simple too.

- `test_services.py`: unit tests for intent, portfolio, and trade services
- `test_graph.py`: workflow and routing tests
- `test_api.py`: FastAPI endpoint tests
- `test_evaluation.py`: evaluation metrics and reporting tests

## Best Fit for This Repo

Your current code is already close to this simplified structure. The main cleanup I would recommend is:

- keep `domain`, `services`, `orchestration`, and `infrastructure` as the core
- move backend code under `api/`
- keep Streamlit under `ui/`
- add a small `observability_service.py`
- make `evaluation/` actually contain runnable evaluation code

## Final Recommendation

If you want something clean but not over-engineered, use this as the target:

1. `domain` for shared models and interfaces
2. `services` for business logic
3. `orchestration` for LangGraph flow
4. `infrastructure` for external integrations
5. `api` and `ui` for entry points
6. `evaluation` for Exercise 2

That is enough to stay modular, follow SOLID reasonably well, and still keep the project easy to build.
