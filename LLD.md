# Low Level Design

## 1. Purpose
This document describes the implemented low-level design of the FastAPI production template in this repository.

The template is designed to be:
- production-oriented
- secure by default
- async-first
- easy to extend
- easy to test
- friendly to both human developers and agentic workflows

Current scope includes:
- FastAPI bootstrap and lifecycle
- versioned APIs under `/api/v1`
- JWT auth with access and refresh tokens
- RBAC with `user` and `admin`
- async PostgreSQL with SQLAlchemy `2.x`
- Alembic migrations
- centralized logging, errors, and middleware
- security headers and auth rate limiting
- layered tests and GitHub Actions workflows

## 2. Design Principles
- Keep HTTP concerns in routers only.
- Keep business logic in services.
- Keep DB access in repositories.
- Keep shared infrastructure in `app/core/`.
- Keep DB setup and models in `app/db/`.
- Add new features as self-contained modules under `app/modules/`.
- Use requirements-first, test-first development for non-trivial features.

## 3. Repository Structure

### 3.1 Top-Level Structure
```text
05_FastAPI/
|-- app/
|-- tests/
|-- alembic/
|-- .github/workflows/
|-- docs/
|-- requirements/
|-- AGENTS.md
|-- CONTEXT.md
|-- LLD.md
|-- README.md
|-- pyproject.toml
|-- .env.example
|-- Makefile
|-- Dockerfile
|-- docker-compose.yml
`-- alembic.ini
```

### 3.2 Application Structure
```text
app/
|-- main.py
|-- api/
|   |-- router.py
|   `-- v1/
|       |-- router.py
|       |-- health.py
|       `-- version.py
|-- common/
|   |-- enums.py
|   `-- responses.py
|-- core/
|   |-- config.py
|   |-- exceptions.py
|   |-- logging.py
|   |-- middleware.py
|   |-- rate_limit.py
|   |-- security.py
|   `-- dependencies.py
|-- db/
|   |-- base.py
|   |-- session.py
|   `-- models/
|       |-- base.py
|       |-- user.py
|       `-- refresh_token.py
`-- modules/
    |-- auth/
    |   |-- dependencies.py
    |   |-- rate_limit.py
    |   |-- repository.py
    |   |-- router.py
    |   |-- schemas.py
    |   `-- service.py
    `-- admin/
        |-- repository.py
        |-- router.py
        `-- service.py
```

### 3.3 Responsibility by Area
| Area | Responsibility |
|---|---|
| `app/main.py` | App factory, lifespan, middleware, exception handlers, API mounting |
| `app/api/` | Versioned router composition only |
| `app/core/` | Shared infrastructure: config, security, logging, errors, middleware, rate limiting |
| `app/db/` | Engine/session setup, ORM base, ORM models |
| `app/modules/` | Feature implementation |
| `tests/` | API, integration, and unit verification |
| `requirements/` | Black-box acceptance criteria for test-first development |

## 4. Architecture

### 4.1 Layered Module Design
Each feature follows this pattern:
- `router.py`: endpoint definitions and metadata
- `schemas.py`: request/response DTOs
- `service.py`: business logic
- `repository.py`: persistence logic
- `dependencies.py`: feature-specific dependencies when needed

This was chosen to:
- keep routers thin
- avoid spreading SQLAlchemy into endpoints
- make testing easier by layer
- keep feature additions predictable

### 4.2 Feature Modules
Current feature modules:
- `auth`
- `admin`

### 4.3 Async Runtime
The request path is async end to end:
- FastAPI
- async SQLAlchemy
- `asyncpg`

## 5. Core Runtime Flow

### 5.1 Generic Flow
`HTTP Request`
-> `RequestContextMiddleware`
-> `SecurityHeadersMiddleware`
-> `CORSMiddleware`
-> `/api/v1 Router`
-> `Feature Router`
-> `Dependencies`
-> `Service`
-> `Repository`
-> `PostgreSQL`
-> `Repository`
-> `Service`
-> `Response Model`
-> `JSON Response`

### 5.2 Authenticated Flow
For `GET /api/v1/auth/me`:
1. request enters middleware chain
2. request ID is assigned or propagated
3. bearer token is read by `oauth2_scheme`
4. JWT is decoded and validated
5. user is loaded from DB
6. active-user check is applied
7. response is serialized as `UserResponse`

### 5.3 Admin Flow
For `GET /api/v1/admin/users`:
1. current user is resolved from access token
2. active-user check is applied
3. role guard verifies `admin`
4. admin service fetches users
5. repository returns users ordered by `id`
6. response is serialized as `list[UserResponse]`

### 5.4 Login Flow
1. router accepts `OAuth2PasswordRequestForm`
2. service normalizes email and validates password
3. repository loads user by email
4. service checks active status
5. service issues access and refresh tokens
6. refresh token hash is stored in DB
7. `TokenResponse` is returned

### 5.5 Refresh Flow
1. router accepts `RefreshTokenRequest`
2. service decodes token as `refresh`
3. service loads refresh token record by `jti`
4. service checks expiration, revoke status, and token hash
5. service loads user and checks active status
6. old refresh token is revoked
7. new access and refresh tokens are issued
8. new refresh token hash is stored

## 6. Configuration Design

`app/core/config.py` uses `pydantic-settings` with `.env` support.

### 6.1 Key Settings
| Setting | Purpose |
|---|---|
| `PROJECT_NAME`, `PROJECT_DESCRIPTION`, `VERSION` | app metadata |
| `ENVIRONMENT`, `DEBUG` | environment behavior |
| `API_V1_PREFIX` | API version prefix |
| `EXPOSE_DOCS` | Swagger/ReDoc exposure |
| `LOG_LEVEL`, `LOG_JSON` | logging mode |
| `BACKEND_CORS_ORIGINS` | CORS allowlist |
| `SECRET_KEY`, `JWT_ALGORITHM` | JWT signing |
| `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` | token TTL |
| `RATE_LIMIT_AUTH` | auth throttle config |
| `DATABASE_URL`, `TEST_DATABASE_URL` | DB connectivity |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_PRE_PING` | DB pool config |

### 6.2 Important Decisions
- secrets come only from environment variables
- `SECRET_KEY` must be at least 32 characters
- CORS CSV values are parsed into lists
- docs exposure is configurable
- default host is `127.0.0.1`

## 7. Middleware, Logging, and Errors

### 7.1 Middleware
| Middleware | Purpose |
|---|---|
| `RequestContextMiddleware` | request ID creation, log context, duration logging, `X-Request-ID` response header |
| `SecurityHeadersMiddleware` | adds secure response headers |
| `CORSMiddleware` | origin/method/header policy from config |

Security headers added:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `X-XSS-Protection: 0`
- `Content-Security-Policy`

### 7.2 Logging
`structlog` is used.

Modes:
- development: readable console logs
- production: JSON logs

Captured fields:
- request ID
- method
- path
- status code
- duration
- startup environment and version

### 7.3 Error Handling
All errors are normalized to:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": [],
    "request_id": "..."
  }
}
```

Handled error types:
- `AppError`
- `HTTPException`
- `RequestValidationError`
- generic `Exception`

Key decisions:
- `request_id` is included when available
- unexpected errors are hidden in production
- validation details are made JSON-safe before serialization

## 8. Security Design

### 8.1 Authentication
Uses:
- `OAuth2PasswordBearer`
- `OAuth2PasswordRequestForm`
- JWT with `HS256`

Access token claims:
- `sub`
- `role`
- `type=access`
- `iat`
- `jti`
- `exp`

Refresh token claims:
- `sub`
- `role`
- `type=refresh`
- `iat`
- `jti`
- `exp`

Decision:
- access tokens include unique `jti` to avoid duplicate token values during fast re-issuance

### 8.2 Password Handling
Uses `pwdlib` with Argon2-based hashing.

Rules:
- raw passwords are never stored
- verification stays in the security/service layer

### 8.3 Refresh Token Strategy
Refresh tokens are persisted server-side using:
- `jti`
- keyed `token_hash`
- `expires_at`
- `revoked_at`

Decision:
- refresh tokens are not stored in plaintext
- rotation revokes the previous token

### 8.4 RBAC
Roles:
- `user`
- `admin`

Dependencies:
- `get_current_user`
- `get_current_active_user`
- `require_role(UserRole.ADMIN)`

Decision:
- permission checks are implemented as dependencies, not inline in route functions

### 8.5 Rate Limiting
Auth endpoints are protected by an in-memory limiter.

Rate-limit key:
- HTTP method
- request path
- client identifier

Client identifier source order:
1. `X-Forwarded-For`
2. `request.client.host`
3. `unknown-client`

Current setting example:
- `5/minute`

Decision:
- simple in-memory limiting is acceptable for template scope
- it can later be swapped for a distributed backend

## 9. Database Design

### 9.1 Database Stack
- PostgreSQL
- SQLAlchemy `2.x`
- `asyncpg`
- Alembic

### 9.2 Session Management
`app/db/session.py` provides:
- `create_async_engine`
- `async_sessionmaker`
- `AsyncSession` dependency
- pool configuration from settings
- engine disposal on shutdown

Important settings:
- `pool_size`
- `max_overflow`
- `pool_pre_ping`
- `expire_on_commit=False`

### 9.3 Base Model
Shared fields:
- `id`
- `created_at`
- `updated_at`

Decision:
- all persistent entities inherit timestamps through a shared mixin

## 10. Data Model

### 10.1 `users`
| Field | Type | Notes |
|---|---|---|
| `id` | integer | primary key |
| `email` | string(320) | unique, indexed |
| `password_hash` | string(255) | hashed password |
| `full_name` | string(255) | required |
| `role` | enum | `user` or `admin` |
| `is_active` | boolean | default `true` |
| `is_verified` | boolean | default `false` |
| `created_at` | timestamptz | server default now |
| `updated_at` | timestamptz | server default now / on update |

### 10.2 `refresh_tokens`
| Field | Type | Notes |
|---|---|---|
| `id` | integer | primary key |
| `user_id` | integer | FK to `users.id` |
| `jti` | string(36) | unique, indexed |
| `token_hash` | string(64) | keyed hash |
| `expires_at` | timestamptz | required |
| `revoked_at` | timestamptz nullable | set on revoke |
| `created_at` | timestamptz | server default now |
| `updated_at` | timestamptz | server default now / on update |

Relationship:
- one `User` to many `RefreshToken`

## 11. DTO Design

### 11.1 Request DTOs
| DTO | Fields | Notes |
|---|---|---|
| `RegisterUserRequest` | `email`, `password`, `full_name` | `EmailStr`, password strength validation, `extra="forbid"` |
| `RefreshTokenRequest` | `refresh_token` | minimal refresh request |
| `OAuth2PasswordRequestForm` | `username`, `password` | `username` is treated as email |

Password rules:
- length 8 to 128
- uppercase required
- lowercase required
- digit required
- special character required

### 11.2 Response DTOs
| DTO | Fields |
|---|---|
| `UserResponse` | `id`, `email`, `full_name`, `role`, `is_active`, `is_verified`, `created_at`, `updated_at` |
| `TokenResponse` | `access_token`, `refresh_token`, `token_type`, `access_token_expires_at`, `refresh_token_expires_at` |
| `HealthResponse` | `status`, `service`, `environment`, `timestamp` |
| `VersionResponse` | `service`, `version`, `environment` |

Decision:
- response DTOs exclude `password_hash` and refresh token records

## 12. API Design

Base prefix:
- `/api/v1`

### 12.1 Endpoints
| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `POST` | `/auth/register` | public | `RegisterUserRequest` | `201 UserResponse` |
| `POST` | `/auth/login` | public | `OAuth2PasswordRequestForm` | `200 TokenResponse` |
| `POST` | `/auth/refresh` | public with refresh validation | `RefreshTokenRequest` | `200 TokenResponse` |
| `GET` | `/auth/me` | authenticated active user | none | `200 UserResponse` |
| `GET` | `/admin/users` | authenticated active admin | none | `200 list[UserResponse]` |
| `GET` | `/health/live` | public | none | `200 HealthResponse` |
| `GET` | `/health/ready` | public | none | `200 HealthResponse` |
| `GET` | `/version` | public | none | `200 VersionResponse` |

### 12.2 Main Error Cases
| Endpoint Area | Typical Errors |
|---|---|
| registration | `validation_error`, `user_already_exists` |
| login | `invalid_credentials`, `inactive_user`, `rate_limit_exceeded` |
| refresh | `invalid_token`, `refresh_token_not_found`, `refresh_token_revoked`, `refresh_token_mismatch`, `inactive_user`, `rate_limit_exceeded` |
| protected user endpoints | `http_401`, `invalid_token`, `inactive_user` |
| admin endpoints | `http_401`, `invalid_token`, `inactive_user`, `insufficient_permissions` |

## 13. Service and Repository Rules

### 13.1 Services
| Service | Responsibilities |
|---|---|
| `AuthService` | normalize email, detect duplicates, hash passwords, verify credentials, issue tokens, validate refresh flow, revoke old refresh token, resolve user from access token |
| `AdminService` | orchestrate admin user listing |

Rule:
- services own orchestration and business rules
- services do not construct HTTP responses directly

### 13.2 Repositories
| Repository | Responsibilities |
|---|---|
| `AuthRepository` | load/create users, create/load/revoke refresh tokens |
| `AdminRepository` | list users ordered by `id` |

Rule:
- repositories are query-focused
- repositories do not own permission logic

## 14. Migrations
Alembic is used for schema evolution.

Current migration:
- `20260409_0001_create_auth_tables.py`

It creates:
- `users`
- `refresh_tokens`
- PostgreSQL enum `user_role`

Decision:
- every schema change must go through Alembic
- enum handling is explicit for PostgreSQL compatibility

## 15. Coding Practices Used
- thin routers
- dependency injection with `Depends`
- env-driven configuration
- explicit request and response models
- centralized errors and logging
- async DB access only
- deterministic admin listing for stable tests
- black-box tests before implementation for non-trivial features
- no hardcoded secrets in business logic

## 16. Testing Strategy

### 16.1 Test Layers
| Layer | Purpose |
|---|---|
| `tests/api/` | endpoint behavior and contracts |
| `tests/integration/` | repository and DB behavior |
| `tests/unit/` | isolated helper and validation logic |

### 16.2 Current Coverage Areas
- auth happy paths
- auth error paths
- password validation
- JWT helper behavior
- refresh token hashing and revocation
- security headers
- auth rate limiting
- RBAC admin access

### 16.3 Test DB Design
- separate PostgreSQL test DB
- `NullPool` for tests
- schema created and dropped around tests
- DB dependency overridden in `tests/conftest.py`

## 17. CI and Delivery

### 17.1 Workflows
| Workflow | Purpose |
|---|---|
| `ci.yml` | dependency sync, Ruff, format check, MyPy, migrations, pytest with coverage |
| `coverage.yml` | test coverage run and artifact upload |
| `security.yml` | Bandit and pip-audit |

### 17.2 Delivery Decisions
- CI uses a clean Python environment
- CI uses a PostgreSQL service container
- quality gates are enforced in automation, not only locally

## 18. Operational Design
- Swagger and ReDoc are exposed only when `EXPOSE_DOCS=true`
- every request gets `X-Request-ID`
- request ID is included in logs and errors when available
- startup and shutdown are logged
- health and version endpoints support operations visibility

## 19. Current Limitations
- auth rate limiting is in-memory and not distributed
- JWT signing currently uses symmetric `HS256`
- no email verification flow
- no password reset flow
- no refresh-token cleanup job

These are acceptable for the current exercise scope.

## 20. Extension Rules
When adding a new feature:
1. create `requirements/<feature>.md`
2. add black-box tests first
3. create `app/modules/<feature>/`
4. define DTOs in `schemas.py`
5. implement persistence in `repository.py`
6. implement business logic in `service.py`
7. implement endpoints in `router.py`
8. register the router in `app/api/v1/router.py`
9. add migrations if schema changes
10. update `README.md`, `CONTEXT.md`, and this document if the design changes

## 21. Key Decisions Summary
- Use layered feature modules for maintainability.
- Centralize shared infrastructure in `app/core/`.
- Centralize DB setup in `app/db/`.
- Use async PostgreSQL with SQLAlchemy `2.x`.
- Use JWT access and refresh tokens with server-side refresh tracking.
- Implement RBAC through dependency-based guards.
- Standardize all errors and logs.
- Protect auth endpoints with rate limiting and security headers.
- Verify the template through layered tests and CI workflows.
