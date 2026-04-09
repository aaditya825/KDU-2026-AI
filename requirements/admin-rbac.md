# Admin RBAC Requirements

This document defines the externally visible behavior for the initial admin-only API surface.

## Goal
- expose at least one authenticated admin-only endpoint to prove role-based access control works end to end
- keep the response free of sensitive fields
- preserve the existing auth behavior for regular users

## Endpoint
- `GET /api/v1/admin/users`

## Authentication And Authorization Rules
- the endpoint requires a valid bearer access token
- unauthenticated requests must return `401`
- authenticated non-admin users must return `403`
- authenticated inactive users must not be allowed through
- authenticated active admin users must return `200`

## Successful Response
- the response body returns a JSON array of user profile objects
- each object includes:
  - `id`
  - `email`
  - `full_name`
  - `role`
  - `is_active`
  - `is_verified`
  - `created_at`
  - `updated_at`
- the response must never include password hashes or refresh tokens
- results should be stable and deterministic for test assertions

## Error Response Rules
- authorization failures must use the standardized error payload shape already used by the API
- non-admin access must use error code `insufficient_permissions`
- unauthenticated access should continue to use the framework-backed `401` error shape already standardized by the app

## Test Generation Guidance
- generate black-box API tests first
- assert only on externally visible behavior
- cover:
  - unauthenticated request
  - authenticated regular user denied
  - authenticated admin allowed
  - response excludes sensitive fields
