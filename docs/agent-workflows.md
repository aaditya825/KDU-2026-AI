# Agent Workflows

This file documents the preferred agent workflows for this repository. The actual reusable project skill lives in `.codex/skills-src/fastapi-prod-template/SKILL.md`.

## 1. Bootstrap Template Infrastructure
Use when setting up project foundations such as packaging, validated settings, Docker support, logging, middleware, migrations, CI, and local development tooling.

Expected output:
- production-oriented scaffolding
- explicit config and environment docs
- baseline quality and security gates

## 2. Implement Authentication Foundation
Use when creating registration, login, refresh-token, current-user, and role-guard capabilities.

Expected output:
- secure password hashing
- JWT access and refresh token flow
- reusable auth dependencies
- DB-backed token lifecycle handling
- auth-focused tests

## 3. Add Secure Feature Module
Use when adding a new API feature under `app/modules/<feature>/`.

Expected output:
- a requirements file or updated acceptance criteria
- black-box tests created before or independently of implementation
- schemas, service, repository, and router
- auth and validation rules
- OpenAPI metadata
- tests and docs updates

## 4. Add Protected Admin Capability
Use when introducing admin-only routes or role-sensitive operations.

Expected output:
- explicit role checks
- unauthorized and forbidden test coverage
- safe logging and standardized errors

## 5. Expand Test and CI Coverage
Use when a feature exists but lacks sufficient confidence or automation.

Expected output:
- deterministic fixtures
- unit, API, and integration coverage where appropriate
- coverage and CI quality gates

## 6. Production Readiness Review
Use before merge or release preparation.

Expected output:
- security gaps identified
- missing tests called out
- logging, docs, and observability gaps listed
- concrete remediation items

## Preferred Prompt Style For Test Generation
When using an agent to generate tests, give it only the requirements document or acceptance criteria and explicitly say:
- do not use implementation details
- generate black-box tests only
- cover happy path, validation failures, auth failures, permission failures, and edge cases
- treat the tests as the acceptance contract for the upcoming implementation
