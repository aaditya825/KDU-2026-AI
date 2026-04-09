# FastAPI Production Template Agent Guide

## Mission
Build and maintain a reusable FastAPI starter template that is production-ready by default: secure, modular, async-first, observable, thoroughly tested, and easy to extend with new features.

## Required Technical Baseline
- Python `3.13`
- FastAPI with async endpoints
- PostgreSQL only for application and test databases
- SQLAlchemy `2.x` async with `asyncpg`
- Pydantic `v2` and `pydantic-settings`
- Alembic for schema migrations
- JWT-based auth with access and refresh tokens
- Argon2-based password hashing via `pwdlib`
- Structured JSON logging
- `pytest`, `pytest-asyncio`, `httpx`, and coverage reporting
- `ruff`, `mypy`, `bandit`, `pip-audit`, pre-commit hooks, and GitHub Actions

## Architecture Rules
- Keep application code under `app/`.
- Use a clear layered design: routers -> services -> repositories -> models.
- Keep cross-cutting infrastructure in `app/core/`.
- Keep database engine, sessions, base models, and ORM models in `app/db/`.
- Keep versioned API composition in `app/api/`.
- Keep feature-specific logic in `app/modules/<feature>/`.
- Keep reusable cross-feature helpers in `app/common/` only when they are broadly reusable.
- Do not introduce business logic into routers or persistence logic into services.

## Configuration and Environment Rules
- All secrets and environment-specific values must come from validated settings classes.
- Never hardcode secrets, credentials, URLs, tokens, or fallback production values.
- Use typed settings such as DSN-aware fields and explicit environment profiles for development, test, and production.
- Every new config value must be documented in `.env.example` and `README.md`.

## Authentication and Authorization Rules
- Use `OAuth2PasswordBearer` and `OAuth2PasswordRequestForm` for token-based login flows.
- Hash passwords with `pwdlib` using Argon2. Never use `hashlib` for password storage.
- Access tokens must be short-lived and include at least `sub`, `role`, and `exp`.
- Refresh tokens must be implemented for production-ready session longevity and must be stored or tracked server-side.
- Authorization must be dependency-based and reusable, including `get_current_user`, active-user checks, and role guards such as admin-only access.
- Never log passwords, password hashes, raw refresh tokens, or bearer tokens.

## Database Rules
- Use `create_async_engine`, `async_sessionmaker`, and `AsyncSession`.
- Configure connection pooling explicitly, including stale connection protection such as `pool_pre_ping`.
- Use a shared base model with `id`, `created_at`, and `updated_at`.
- Persistent schema changes require Alembic migrations.
- Repositories own SQLAlchemy queries. Services coordinate business logic.
- Use unique indexes and intentional indexing for lookup-heavy columns such as user email.

## Validation and Security Rules
- All request and response contracts must use Pydantic models.
- Use strong types such as `EmailStr`, constrained fields, and custom validators where appropriate.
- Enforce password strength validation.
- CORS must use an explicit allowlist from configuration. Never use wildcard origins with credentials enabled.
- Add rate limiting to authentication-sensitive routes.
- Add security-focused middleware or headers suitable for production.
- Never build SQL with string formatting.

## Error Handling and Logging Rules
- Use centralized exception handlers for framework, validation, auth, permission, not-found, domain, and unexpected errors.
- Keep one standardized error response shape across the API.
- Use structured JSON logging in production and allow a more readable development mode locally.
- Include correlation or request IDs in request lifecycle logs and error logs.
- Log method, path, status, duration, environment, and authenticated user ID when available and safe.
- Do not expose stack traces or internal implementation details in production responses.

## Testing and Quality Rules
- Follow strict test-first development for new features whenever feasible.
- Start with a feature requirements file in `requirements/` or an equivalent acceptance-criteria document before implementation.
- Generate or write black-box tests from the requirements only, without depending on implementation details.
- Review and keep the tests before implementation begins.
- New features must ship with unit tests and API or integration coverage.
- Keep a separate test database configuration. Do not share development state with tests.
- Use fixtures for DB sessions, authenticated clients, and user factories.
- Use dependency overrides where mocking is appropriate.
- Maintain at least 70 percent coverage overall, with stronger coverage expectations for auth and security-critical paths.
- Code is not complete until lint, type checks, tests, and coverage expectations are satisfied.

## Documentation Rules
- Every endpoint should include tags, summaries, descriptions, and response models.
- Provide request or response examples for externally consumed endpoints.
- Keep `README.md` updated with setup, environment variables, run instructions, test instructions, extension guidance, and deployment notes.
- Keep `CONTEXT.md` updated with implementation status, important decisions, current constraints, and next steps.
- Keep feature acceptance criteria in `requirements/` when building or extending non-trivial features.
- Keep architectural and workflow docs aligned with the actual code layout.

## Extensibility Rules
- A new feature should primarily require changes inside one feature module, its tests, and relevant docs.
- If a feature requires broad edits across unrelated folders, pause and simplify the design before continuing.
- Prefer explicit contracts between layers and avoid circular imports or hidden shared state.

## Guidance Sources
- Current implementation state lives in `CONTEXT.md`.
- Feature-level acceptance criteria should live in `requirements/`.
- Global implementation workflow lives in `docs/implementation-playbook.md`.
- Architectural boundaries live in `docs/project-architecture.md`.
- Agent workflow summaries live in `docs/agent-workflows.md`.
- The reusable project skill lives in `.codex/skills-src/fastapi-prod-template/SKILL.md`.
