# Feature Requirements

This folder stores feature-level requirement and acceptance-criteria documents used for strict test-first development.

## Purpose
- define feature behavior before implementation
- give agents a black-box source of truth for test generation
- separate acceptance criteria from implementation details

## Recommended Pattern
- create one file per feature or major capability
- use names such as `auth.md`, `users.md`, or `admin-access.md`
- describe behavior in terms of inputs, outputs, rules, and failure cases
- avoid implementation details such as function names, class names, or internal module structure

## Minimum Contents For Each Requirement File
- feature goal
- public endpoints or user-visible behavior
- validation rules
- auth and permission rules
- error cases
- edge cases
- acceptance criteria

## Workflow
1. Write or update the feature requirements file.
2. Generate black-box tests using only the requirements file.
3. Review and keep the tests.
4. Implement code to make those tests pass.
5. Update `CONTEXT.md` once the implementation step is complete.
