# Project Architecture

## Objectives
This template should be reusable, secure, modular, and easy to extend without reworking core infrastructure every time a new API feature is added.

## Recommended Repository Layout

```text
05_FastAPI/
|-- AGENTS.md
|-- README.md
|-- pyproject.toml
|-- .env.example
|-- .pre-commit-config.yaml
|-- Makefile
|-- Dockerfile
|-- docker-compose.yml
|-- alembic.ini
|-- .github/
|   `-- workflows/
|-- docs/
|   |-- project-architecture.md
|   |-- implementation-playbook.md
|   `-- agent-workflows.md
|-- scripts/
|-- alembic/
|   |-- env.py
|   `-- versions/
|-- app/
|   |-- AGENTS.md
|   |-- main.py
|   |-- api/
|   |   |-- router.py
|   |   `-- v1/
|   |       |-- router.py
|   |       |-- health.py
|   |       `-- version.py
|   |-- core/
|   |   |-- config.py
|   |   |-- security.py
|   |   |-- logging.py
|   |   |-- exceptions.py
|   |   |-- middleware.py
|   |   `-- dependencies.py
|   |-- db/
|   |   |-- base.py
|   |   |-- session.py
|   |   `-- models/
|   |       |-- base.py
|   |       |-- user.py
|   |       `-- refresh_token.py
|   |-- common/
|   |   |-- responses.py
|   |   |-- enums.py
|   |   `-- utils.py
|   `-- modules/
|       |-- auth/
|       |   |-- router.py
|       |   |-- schemas.py
|       |   |-- service.py
|       |   |-- repository.py
|       |   `-- dependencies.py
|       `-- users/
|           |-- router.py
|           |-- schemas.py
|           |-- service.py
|           `-- repository.py
|-- tests/
|   |-- AGENTS.md
|   |-- conftest.py
|   |-- unit/
|   |-- api/
|   `-- integration/
`-- .codex/
    `-- skills-src/
        `-- fastapi-prod-template/
            `-- SKILL.md
```

## Layer Responsibilities
- `app/api/` composes versioned routers and keeps public route registration explicit.
- `app/modules/` contains feature-local contracts and logic.
- `app/core/` contains infrastructure policies that should not be duplicated per feature.
- `app/db/` contains the async engine, session factory, base models, and ORM entities.
- `tests/` mirrors behavior layers rather than mirroring the file tree.

## Required Foundational Capabilities
- API versioning under `/api/v1`
- health and readiness endpoints
- version endpoint
- JWT access and refresh token flow
- role-based authorization
- structured request logging with correlation IDs
- centralized exception handling
- async PostgreSQL integration
- migrations via Alembic
- Docker-ready local setup
- CI quality gates

## Extension Rule
When a new feature is added, most work should stay inside one feature module plus tests and documentation. If a change requires edits across many unrelated folders, reconsider the design before implementation.

## Why This Structure
- It avoids oversized route files and shared service dumping grounds.
- It keeps reusable infrastructure centralized.
- It makes auth, logging, and error handling consistent across features.
- It gives agents a predictable place to add code, tests, docs, and migrations.
