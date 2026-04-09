# FastAPI Production Template

Reusable FastAPI starter template for building secure, async-first, production-oriented APIs with JWT auth, PostgreSQL, structured logging, Alembic migrations, and layered tests.

## What This Template Includes
- FastAPI app bootstrap with versioned routing under `/api/v1`
- JWT authentication with access and refresh tokens
- role-based authorization with `user` and `admin` roles
- async SQLAlchemy `2.x` + PostgreSQL via `asyncpg`
- Alembic migrations
- Pydantic v2 request and response validation
- structured logging with request IDs
- standardized JSON error responses
- CORS, security headers, and auth endpoint rate limiting
- API, unit, and integration tests with `pytest`
- Docker, Docker Compose, pre-commit, Ruff, MyPy, Bandit, and GitHub Actions

## Project Structure
```text
app/
  api/
    v1/
  common/
  core/
  db/
    models/
  modules/
    admin/
    auth/
tests/
  api/
  integration/
  unit/
alembic/
.github/workflows/
requirements/
docs/
demo-ui/
```

## Implemented API Surface
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `GET /api/v1/admin/users`
- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `GET /api/v1/version`
- `GET /docs` and `GET /redoc` when `EXPOSE_DOCS=true`

## Local Setup
1. Copy `.env.example` to `.env`.
2. Update the secret and database settings.
3. Install dependencies:

```bash
uv sync --all-extras
```

4. Start the databases if needed:

```bash
docker compose up -d db test-db
```

5. Apply migrations:

```bash
make db-upgrade
```

6. Run the application:

```bash
make run
```

## Startup Commands
If `make` is available:

```bash
docker compose up -d db test-db
make db-upgrade
make run
streamlit run demo-ui/streamlit_app.py
```

If you are on Windows Git Bash without `make` or `uv`, use:

```bash
docker compose up -d db test-db
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
python -m streamlit run demo-ui/streamlit_app.py
```

Backend:

```text
http://127.0.0.1:8000
```

Demo UI:

```text
http://localhost:8501
```

## Demo UI
A separate demo UI is available in `demo-ui/README.md`.

It is now implemented with Streamlit and is meant for showcasing the backend directly in the browser. It includes:
- health and version checks
- register and login
- refresh token rotation
- current user lookup
- admin user listing
- a request and response log panel

To run it locally:

```bash
streamlit run demo-ui/streamlit_app.py
```

Then open:

```text
http://localhost:8501
```

## Environment Variables
Required settings are already listed in `.env.example`.

The most important ones are:
- `ENVIRONMENT`
- `SECRET_KEY`
- `DATABASE_URL`
- `TEST_DATABASE_URL`
- `BACKEND_CORS_ORIGINS`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `RATE_LIMIT_AUTH`

## Useful Commands
```bash
make install
make run
make lint
make format
make typecheck
make test
make coverage
make security
make test-db-up
make db-upgrade
make db-revision m="describe_change"
streamlit run demo-ui/streamlit_app.py
```

## Testing And Quality Gates
Local verification targets:
- `ruff check .`
- `mypy app tests`
- `pytest --cov=app --cov-report=term-missing`
- `bandit -r app`
- `pip-audit`

Current verified local results in this workspace:
- full test suite: `31 passed`
- coverage: `86.40%`
- Ruff: passed
- MyPy: passed
- Bandit: passed

Notes:
- local `pip-audit` on this machine queried the workstation-wide Python environment, which included unrelated global packages outside this repo
- the repository now pins safer project dependency floors and the GitHub Actions security workflow runs in a clean environment for project-scoped verification

## CI Workflows
The repository includes:
- `.github/workflows/ci.yml`
- `.github/workflows/coverage.yml`
- `.github/workflows/security.yml`

These workflows run linting, formatting checks, typing, migrations, tests with coverage, and dependency/security scans.

## Extending The Template
When adding a new feature:
1. Create a requirements file in `requirements/` with black-box acceptance criteria.
2. Add API or integration tests first.
3. Implement the feature in `app/modules/<feature>/`.
4. Keep HTTP concerns in `router.py`, business logic in `service.py`, and DB access in `repository.py`.
5. Update migrations if models change.
6. Update `README.md` and `CONTEXT.md` when behavior changes.

## Security Notes
- passwords are hashed with `pwdlib` using Argon2
- access and refresh tokens are signed and validated server-side
- refresh tokens are persisted and revoked on rotation
- auth endpoints are rate limited
- responses include security headers
- CORS is allowlist-based and environment-driven
- secrets are loaded from environment variables only

## Guidance Files
- `AGENTS.md`: repository-wide engineering rules for Codex
- `CONTEXT.md`: machine-facing implementation state and verification notes
- `docs/project-architecture.md`: structure and layer ownership
- `docs/implementation-playbook.md`: workflow and definition of done
- `docs/agent-workflows.md`: recommended agentic workflows
- `requirements/`: feature acceptance criteria for test-first implementation

## Current Status
The exercise requirements for the production-ready starter template have been implemented in the repository codebase.

Optional next improvements beyond the exercise:
- background job integration
- email verification and password reset flows
- refresh token cleanup jobs
- deployment manifests for a target platform
