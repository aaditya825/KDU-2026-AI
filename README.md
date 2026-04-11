# Multimodal AI Assistant

A production-ready MVP implementing the Hybrid Service Layer + LCEL Skeleton architecture.

## Implemented Features

- **General text chat** – Context-aware responses with structured JSON output
- **Weather tool calling** – Model-driven weather lookups with real Open-Meteo data and location inference from user profiles
- **Image analysis** – Multimodal image understanding with structured outputs
- **Session-scoped memory** – Conversation history management per session
- **Dynamic behavior** – User-controlled communication style, expertise level, and response length
- **User profiles** – Hidden context for user identity and location
- **Structured outputs** – Typed JSON responses for all routes (text, weather, image)
- **Layered backend** – Clear separation between API, orchestration, services, and LangChain chains

## Architecture

See [implementation_lld.md](implementation_lld.md) for detailed architecture diagrams and component breakdown.

Tech stack:
- **Frontend**: Streamlit
- **Backend**: FastAPI
- **LLM orchestration**: LangChain LCEL
- **Model**: Google Gemini
- **Weather data**: Open-Meteo

## Getting Started

### Prerequisites

- Python 3.10+
- `GEMINI_API_KEY` environment variable set

### Installation

Install dependencies:

```powershell
python -m pip install -e .[dev]
```

### Run Locally

**Backend** (runs on `http://localhost:8000`):

```powershell
uvicorn src.assistant.backend.main:app --reload
```

**Frontend** (runs on `http://localhost:8501`):

```powershell
streamlit run src/assistant/frontend/streamlit_app.py
```

The frontend will connect to the backend at `http://localhost:8000`.

### Run Tests

Unit tests:

```powershell
pytest tests/unit/
```

Integration tests:

```powershell
pytest tests/integration/
```

## Configuration

Set these environment variables:

```env
GEMINI_API_KEY=<your-api-key>
ASSISTANT_MODEL=gemini-2.5-flash
WEATHER_GEOCODING_URL=https://geocoding-api.open-meteo.com/v1/search
WEATHER_FORECAST_URL=https://api.open-meteo.com/v1/forecast
WEATHER_TIMEOUT_SECONDS=10.0
```

## Documentation

- [implementation_lld.md](implementation_lld.md) – Low-level design with architecture diagrams and component breakdown
- [AGENTS.md](AGENTS.md) – Repository structure and architecture rules
- [docs/mvp_approaches/04_hybrid_service_lcel_mvp.md](docs/mvp_approaches/04_hybrid_service_lcel_mvp.md) – System of record for the current architecture
