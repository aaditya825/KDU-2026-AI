# FastAPI Production Template Skill

## Purpose
Use this skill when building or extending features in this repository. The goal is to keep every change aligned with production-grade FastAPI practices.

## Apply This Skill When
- creating shared project infrastructure
- adding or extending authentication behavior
- adding a protected endpoint
- creating a new feature module
- improving production-readiness for an existing feature

## Required Outcomes
- follow the layered design: router -> service -> repository -> model
- keep routers thin and metadata-rich
- use validated Pydantic request and response schemas
- keep persistence logic in repositories
- use async SQLAlchemy patterns with explicit session boundaries
- use test-first development for non-trivial features
- add tests for success, validation, auth, and permission paths
- update docs when setup, behavior, or extension guidance changes

## Standard Workflow
1. Read `AGENTS.md`, `app/AGENTS.md`, and `tests/AGENTS.md`.
2. Read `CONTEXT.md` to understand what is already implemented and what the next step is.
3. Read `docs/implementation-playbook.md` before changing architecture or workflow conventions.
4. Read or create a feature requirements file in `requirements/`.
5. Generate or write black-box tests from the requirements before implementation.
6. If the change is structural, confirm alignment with `docs/project-architecture.md`.
7. Create or extend the feature module under `app/modules/<feature>/`.
8. Define schemas before route logic.
9. Keep settings, hashing, token logic, middleware, and exception mapping centralized.
10. Add lower-level unit or integration tests as needed after the acceptance tests exist.
11. Verify that logging, validation, and error handling remain standardized.
12. Update `CONTEXT.md` with implementation progress and update `README.md` or `docs/` if setup, usage, or extension guidance changed.

## Guardrails
- do not hardcode secrets, credentials, or fallback production values
- do not place business logic directly in routers
- do not bypass validation with untyped request handling
- do not use raw password hashing primitives for password storage
- do not skip refresh-token handling when extending auth flows
- do not generate tests by reading the implementation first when a requirement-driven test-first workflow is possible
- do not consider a feature complete without tests and docs alignment

## Completion Checklist
- module structure is consistent
- auth and permission behavior is explicit
- async DB access is isolated and safe
- errors are standardized
- logs are structured and safe
- tests cover happy and unhappy paths
- docs stay aligned with implementation
