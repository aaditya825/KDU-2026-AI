# Test Guide

## Purpose
This folder verifies that the template behaves like production software and remains safe to extend as features are added.

## Test-First Rule
- For new features, prefer writing tests before implementation code exists.
- Generate tests from a requirements file or explicit acceptance criteria, not from the implementation.
- Keep tests black-box where possible: input, output, status code, error shape, and visible behavior.
- Avoid coupling tests to internal helper names or private implementation details unless writing focused unit tests.

## Test Layers
- `tests/unit/` for isolated services, utilities, security helpers, validators, and settings behavior.
- `tests/api/` for HTTP contracts, validation failures, auth requirements, error responses, and OpenAPI-facing behavior.
- `tests/integration/` for repository behavior, database-backed workflows, migrations, and multi-layer feature paths.

## Required Coverage Areas
- registration, login, token refresh, and protected-route access
- active-user and role-based authorization behavior
- validation errors for malformed or weak input
- standardized error payloads and exception mapping
- repository behavior against a real test database
- health and readiness endpoints

## Fixture Rules
- Prefer reusable fixtures in `conftest.py`.
- Provide fixtures for async DB session, test client, authenticated client, and user factories.
- Keep test data isolated and deterministic.
- Use dependency overrides when unit tests need mocked collaborators.

## Database Test Rules
- Use a separate PostgreSQL test database, never the development database.
- Prefer migrations or explicit schema setup that matches production structure.
- Integration tests should prove that persistence behavior works with real async sessions.

## Quality Rules
- Cover happy paths and failure modes.
- Every protected endpoint must have unauthenticated and unauthorized test cases.
- Security-sensitive code paths should be treated as regression-critical.
- Avoid brittle snapshot-only tests when explicit assertions are clearer.
- Maintain coverage at or above the project threshold.
