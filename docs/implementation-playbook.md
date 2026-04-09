# Implementation Playbook

## Goal
Build a reusable FastAPI template that is secure, observable, async-first, and easy to extend while remaining faithful to production engineering standards.

## Required Tooling
- package and project config in `pyproject.toml`
- `ruff`, `mypy`, `bandit`, `pip-audit`, `pytest`, `pytest-cov`, and `pytest-asyncio`
- pre-commit hooks
- `Makefile` for common commands such as lint, test, run, and migration tasks
- Dockerfile and Docker Compose for local development and test database support

## Default Development Workflow
1. Write or update a feature requirements file in `requirements/`.
2. Generate or write black-box tests from the requirements only.
3. Review the tests and keep them as the acceptance contract.
4. Implement code to make the tests pass.
5. Refactor only after the behavior contract is protected by tests.
6. Update `CONTEXT.md` and user-facing docs once the feature is stable.

## Recommended Implementation Order
1. Create packaging, linting, typing, security, and local task tooling.
2. Create validated settings with `pydantic-settings`, env profiles, and `.env.example`.
3. Bootstrap FastAPI app structure with lifespan, middleware, exception handlers, and `/api/v1` composition.
4. Add health, readiness, and version endpoints.
5. Add async SQLAlchemy engine, session dependency, base models, and Alembic setup.
6. Implement user and refresh-token persistence models with proper indexes and timestamps.
7. Implement auth flows: registration, login, refresh, current-user access, and role guards.
8. Add CORS, rate limiting, security headers, and structured logging.
9. Add tests, coverage, and CI pipelines.
10. Finalize README and extension guidance.

## Authentication and Authorization Expectations
- Use `OAuth2PasswordBearer` and `OAuth2PasswordRequestForm`.
- Hash passwords with `pwdlib` using Argon2.
- Keep access tokens short-lived and include `sub`, `role`, and expiration claims.
- Implement refresh tokens and track them server-side.
- Add dependencies for current user, current active user, and role requirements.
- Do not return sensitive fields from auth endpoints.

## Database Expectations
- Use `create_async_engine` with `asyncpg`.
- Configure pooling intentionally with settings such as pool size, overflow, and stale connection checks.
- Expose an async DB dependency through `AsyncSession`.
- Keep ORM base models shared and timestamped.
- Use Alembic for every schema change.
- Use repositories for CRUD and query behavior instead of embedding SQLAlchemy calls throughout the app.

## Security Expectations
- Validate all input with Pydantic `v2`.
- Use strong field types such as `EmailStr` and constrained password fields plus custom validators.
- Enforce CORS with explicit allowed origins from config.
- Add rate limiting to auth-sensitive routes.
- Add security headers and avoid exposing framework internals.
- Never trust client-provided role, identity, or permission state without verification.

## Error and Logging Expectations
- Centralize exception handling for validation, auth, permission, domain, DB, and unexpected failures.
- Standardize the error response shape across all endpoints.
- Use structured JSON logging in production and readable logs in development.
- Include request ID, path, method, status, duration, environment, and authenticated user ID when safe.

## How To Add a New Feature
1. Create or update `requirements/<feature>.md` with acceptance criteria.
2. Generate or write black-box tests from that requirements file before implementation.
3. Create `app/modules/<feature>/`.
4. Start with `schemas.py` to define request and response contracts.
5. Add `repository.py` for persistence operations.
6. Add `service.py` for business rules and orchestration.
7. Add `router.py` for HTTP endpoints, auth dependencies, metadata, and response models.
8. Add `dependencies.py` only if the feature needs custom route dependencies.
9. Register the router in the API composition layer.
10. Add lower-level unit coverage where needed after the behavior-level tests exist.
11. Update docs and examples if public behavior changed.

## Definition of Done
A feature is not complete until it has:
- an explicit requirements or acceptance-criteria document when the feature is non-trivial
- validated request and response schemas
- clear auth and permission rules
- standardized error handling
- structured logging at meaningful boundaries
- unit and API or integration tests
- docs updates if public behavior changed
- migration coverage when persistent schema changed

## Review Checklist
- Was the feature specified before implementation?
- Were black-box tests written from the requirements before or independently of the implementation?
- Is the router thin and metadata-rich?
- Is business logic in the service layer?
- Is persistence isolated in the repository?
- Are config values validated and environment-driven?
- Are tokens, passwords, and secrets handled safely?
- Are error responses standardized?
- Are success, validation, auth, and permission failures tested?
- Would adding a related endpoint fit the same module cleanly?
