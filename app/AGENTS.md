# App Layer Guide

## Purpose
This folder contains all application code. Treat it as production software, not a demo. Every feature must be secure, testable, and easy to extend.

## Expected Layout
- `app/main.py` bootstraps FastAPI, lifespan, middleware, exception handlers, and router registration.
- `app/api/` contains API composition and versioned entrypoints such as `/api/v1`.
- `app/core/` contains settings, security helpers, middleware, logging, exception mapping, and shared dependencies.
- `app/db/` contains engine setup, async session management, base models, and ORM models.
- `app/modules/<feature>/` contains feature-local router, schemas, service, repository, and optional dependencies.
- `app/common/` contains shared enums, response models, utility helpers, and other truly cross-feature concerns.

## Router Rules
- Routers define the HTTP contract, status codes, dependency wiring, tags, summaries, and response models.
- Routers must remain thin and should call services instead of embedding business logic.
- Do not access SQLAlchemy sessions directly in routers except through service or dependency boundaries.
- Every non-trivial endpoint should include OpenAPI-friendly metadata and examples where useful.

## Service Rules
- Services own business workflows, invariants, and orchestration between repositories and shared helpers.
- Services should be stateless and straightforward to unit test.
- Services should raise typed domain exceptions rather than returning ad hoc error payloads.
- Keep security-sensitive rules explicit in services when they represent domain decisions rather than framework dependencies.

## Repository Rules
- Repositories own persistence logic and SQLAlchemy query construction.
- Use async SQLAlchemy `2.x` patterns only.
- Keep transaction boundaries deliberate and consistent.
- Prefer indexed lookups, explicit eager-loading strategy when needed, and safe parameterized queries.

## Data and Model Rules
- Base ORM models must include `id`, `created_at`, and `updated_at`.
- User-related persistence must support normalized email lookups, password hashing, role storage, and active-state checks.
- Add migrations whenever persistent schema changes are introduced.

## Security Rules
- Centralize hashing, token generation, token verification, and auth helpers in `app/core/security.py`.
- Use `OAuth2PasswordBearer` for bearer auth and explicit dependencies for current-user and role requirements.
- Access tokens must remain short-lived. Refresh flows must be handled explicitly and securely.
- Apply password strength checks before persistence.
- Never leak secret material into logs, exceptions, or API responses.
- Add rate limiting and security headers in shared middleware rather than feature routers.

## Configuration Rules
- Use `pydantic-settings` for all environment-driven configuration.
- Validate required settings at startup.
- Keep separate config for development, test, and production behavior where log level, docs exposure, or CORS may differ.

## Logging and Error Rules
- Raise typed exceptions and let centralized handlers create the standardized error response.
- Use structured logging instead of print statements.
- Ensure request logging includes request ID, path, method, status, and duration.
- Do not return raw stack traces to clients.
