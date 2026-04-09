# Implementation Context

This file is the machine-facing running context for the repository. Keep it updated as implementation progresses so future work can build on current decisions without overloading `README.md`.

## Purpose
- track what has already been implemented
- record important architectural and tooling decisions
- note current constraints, assumptions, and known gaps
- list the next concrete implementation steps

## Project Intent
Build a reusable, production-grade FastAPI starter template that is secure, async-first, modular, observable, and easy to extend.

## Current State
The repository now contains a completed production-ready FastAPI starter template that satisfies the exercise requirements.

Implemented so far:
- root project tooling and packaging via `pyproject.toml`
- local development helpers via `Makefile`
- Docker and Docker Compose scaffolding
- `.env.example` with typed-config-oriented environment variables
- pre-commit config and `.gitignore`
- FastAPI bootstrap in `app/main.py`
- versioned API composition under `app/api/`
- health and version endpoints under `/api/v1`
- typed settings using `pydantic-settings`
- centralized exception formatting
- request ID middleware
- structured logging bootstrap
- shared response schemas for health, version, and standardized error payloads
- async SQLAlchemy engine and session dependency
- ORM base model plus `User` and `RefreshToken` entities
- auth module with register, login, refresh, and current-user flows
- JWT access and refresh token generation plus server-side refresh token tracking
- Alembic env wiring and initial auth migration
- initial async API tests for auth flows
- a formal requirements document for the upcoming security hardening feature
- security headers middleware for API responses
- auth endpoint rate limiting with standardized `429` responses
- black-box security-hardening API tests generated from the requirements document
- verified security-hardening API tests passing against the PostgreSQL test database
- broader API, unit, and integration auth/security test coverage
- admin-only API surface for RBAC verification
- GitHub Actions workflows for CI, coverage, and security checks
- OpenAPI request and response examples on primary schemas
- project guidance and agent workflow files

## Current Architecture Decisions
- Use a layered structure: routers -> services -> repositories -> models.
- Keep cross-cutting infrastructure in `app/core/`.
- Keep DB setup and ORM models in `app/db/`.
- Keep feature-specific behavior in `app/modules/<feature>/`.
- Keep API routing versioned under `/api/v1`.
- Keep `README.md` human-friendly and use this file for implementation state tracking.
- Use a strict test-first workflow for new non-trivial features: requirements file first, black-box tests second, implementation third.

## Current Root Files
- `pyproject.toml`: package metadata and tooling configuration
- `.env.example`: environment template
- `Dockerfile`: container image build
- `docker-compose.yml`: local app and PostgreSQL services
- `Makefile`: common dev commands
- `AGENTS.md`: global Codex engineering rules
- `CONTEXT.md`: implementation state and decisions
- `requirements/`: feature-level acceptance criteria for test-first development

## App Foundation Implemented
- `app/main.py`
  - FastAPI app factory
  - app lifespan logging
  - middleware registration
  - exception handler registration
  - versioned router inclusion
- `app/core/config.py`
  - cached typed settings
  - env-driven toggles for docs, logging, CORS, secrets, and DB config
- `app/core/logging.py`
  - structlog-based logging configuration
  - JSON logging in production-oriented mode
- `app/core/middleware.py`
  - request ID propagation
  - request completion logging
  - CORS middleware registration
- `app/core/exceptions.py`
  - standardized application error shape
  - handlers for HTTP, validation, custom app, and unexpected exceptions
- `app/api/v1/health.py`
  - liveness endpoint
  - readiness endpoint
- `app/api/v1/version.py`
  - service version metadata endpoint

## Persistence and Auth Implemented
- `app/db/session.py`
  - async engine setup
  - session factory
  - DB session dependency
- `app/db/models/base.py`
  - shared base model with `id`, `created_at`, and `updated_at`
- `app/db/models/user.py`
  - user persistence model
  - role and active-state fields
- `app/db/models/refresh_token.py`
  - refresh token persistence model
  - token rotation support
- `app/core/security.py`
  - password hashing helpers
  - JWT access and refresh token creation
  - token decode and token hashing helpers
- `app/modules/auth/`
  - auth schemas
  - repository
  - service
  - dependencies
  - router
- `alembic/env.py` and `alembic/versions/20260409_0001_create_auth_tables.py`
  - migration wiring
  - initial auth schema
- `tests/conftest.py` and `tests/api/test_auth.py`
  - async test DB setup
  - auth flow coverage

## Security Hardening Implemented
- `requirements/security-hardening.md`
  - black-box acceptance criteria for security headers and rate limiting
- `app/core/rate_limit.py`
  - in-memory rate limit tracking and rate string parsing
- `app/modules/auth/rate_limit.py`
  - auth endpoint rate-limit enforcement
- `app/core/middleware.py`
  - security headers added to API responses
- `app/core/exceptions.py`
  - app error responses now support response headers such as `Retry-After`
- `tests/api/test_security_hardening.py`
  - black-box coverage for security headers and rate limiting behavior

## RBAC Admin Surface Implemented
- `requirements/admin-rbac.md`
  - black-box acceptance criteria for the initial admin-only API surface
- `app/modules/admin/repository.py`
  - repository query for deterministic user listing
- `app/modules/admin/service.py`
  - admin service layer for user listing
- `app/modules/admin/router.py`
  - `GET /api/v1/admin/users` protected by active-admin authorization
- `tests/api/test_admin_rbac.py`
  - unauthenticated denial
  - non-admin denial
  - successful admin access with no sensitive fields returned

## Broader Test Coverage Implemented
- `tests/api/test_auth_errors.py`
  - duplicate registration, validation, invalid login, invalid refresh, unauthenticated `/me`, and email normalization coverage
- `tests/unit/test_auth_schemas.py`
  - password policy validation coverage at the schema layer
- `tests/unit/test_security_helpers.py`
  - password hashing, token claims, token type validation, and refresh-token hashing coverage
- `tests/integration/test_auth_repository.py`
  - repository-level coverage for user persistence and refresh-token revoke behavior
- `app/core/exceptions.py`
  - error details are now JSON-safe for validation failures
- `app/core/logging.py`
  - console logging now formats exceptions correctly in non-JSON mode

## Delivery And Verification Implemented
- `.github/workflows/ci.yml`
  - lint, format check, type-check, migrations, and test execution
- `.github/workflows/coverage.yml`
  - coverage run with artifact upload
- `.github/workflows/security.yml`
  - Bandit and pip-audit in CI
- `README.md`
  - expanded setup, commands, extension workflow, CI, and security notes
- `pyproject.toml`
  - safer dependency floors for FastAPI and Starlette in response to audit findings
  - dev dependency pins for `Pygments` and `requests`

## Verification Results
- targeted security-hardening suite: passed
- broader auth/security suite: passed
- full suite: `31 passed`
- coverage: `86.40%`
- Ruff: passed
- MyPy: passed
- Bandit: passed
- Alembic upgrade against PostgreSQL test DB: passed
- local `pip-audit` required network access and reported vulnerabilities from the workstation-wide Python environment, including packages not owned by this repo; the project manifest was updated with safer direct dependency floors and CI now runs the audit in a clean environment

## Known Constraints
- Dependencies are installed in this workspace.
- The targeted security-hardening test suite has been verified against the PostgreSQL test database service.
- The broader targeted auth/security test suite is now passing locally: `17 passed`.
- The full project test suite now passes end-to-end locally.
- The project is not yet initialized as a Git repository in this folder.
- This machine's global Python environment contains unrelated packages outside the repo; local `pip-audit` therefore reflects more than the template alone.

## Next Recommended Step
The exercise scope is complete.

Optional next steps beyond the assignment:
1. add email verification and password reset flows
2. add token/session cleanup jobs
3. add deployment manifests for a target platform
4. initialize Git and open the first PR

## Update Rule
Whenever implementation meaningfully changes, update:
- what was added
- any new architectural decisions
- any new constraints or assumptions
- the next recommended step
