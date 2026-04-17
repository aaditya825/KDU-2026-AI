# Gemini Feature Implementation Plan

This document defines the exact implementation steps for the next three useful features to add to this resume-shortlister MCP project using Gemini:

1. `shortlist_candidates_for_job`
2. `extract_candidate_profile`
3. `generate_interview_pack`

The plan assumes the current codebase remains a Python stdio MCP server under `MCP/solutions` and that Gemini replaces the current OpenAI-backed LLM logic for the enhanced workflows.

## Goal

Convert the current single-resume helper into a recruiter workflow tool that can:

- rank multiple resumes for one job description
- normalize resume data into structured candidate profiles
- generate interview packs for shortlisted candidates

## Implementation Order

Implement the features in this order:

1. Gemini integration foundation
2. `extract_candidate_profile`
3. `shortlist_candidates_for_job`
4. `generate_interview_pack`
5. docs and validation cleanup

That order is deliberate. The profile extractor creates reusable structured data, the shortlist feature depends on that normalization, and the interview pack uses both the profile and the job match output.

## Phase 1: Gemini Integration Foundation

### Step 1: Add dependencies

Update `MCP/solutions/requirements.txt` to add the Gemini SDK and keep existing dependencies unless intentionally removed.

Add:

- `google-generativeai` or the currently chosen Gemini Python SDK

### Step 2: Introduce Gemini configuration

Update the enhanced server configuration to read:

- `GEMINI_API_KEY`
- optional `GEMINI_MODEL` with a default such as `gemini-1.5-pro` or the chosen stable model

Keep `RESUME_DIR`.

### Step 3: Create a dedicated Gemini utility module

Add a new utility module under `MCP/solutions/utils`, for example `gemini_utils.py`.

This module should contain:

- Gemini client initialization
- a helper to call Gemini with plain text prompts
- a helper to request JSON-only structured output
- centralized error handling and model fallback behavior

### Step 4: Separate provider-specific logic from business logic

Refactor the current enhanced server so business workflows do not directly depend on LangChain/OpenAI classes.

Create utility functions for:

- loading resume text
- chunking long resume text if needed
- prompting Gemini for structured outputs
- formatting MCP tool responses

The server file should only orchestrate tool input validation, call the workflow utility, and return `TextContent`.

## Phase 2: Structured Candidate Profiles

### Step 5: Add the `extract_candidate_profile` MCP tool

Add a new tool to the enhanced server:

- name: `extract_candidate_profile`

Input schema:

- `file_path: str`
- `output_format: str = "json"`

Supported values for `output_format`:

- `json`
- `summary`

### Step 6: Define the candidate profile schema

Gemini should return a strict JSON object with these fields:

- `name`
- `contact`
- `location`
- `current_title`
- `seniority_level`
- `estimated_years_experience`
- `skills`
- `tools_and_platforms`
- `programming_languages`
- `work_experience`
- `education`
- `projects`
- `certifications`
- `work_authorization`
- `summary`

Use conservative extraction rules:

- only populate sensitive fields if explicitly present
- use `null` when not confidently available
- do not infer protected attributes

### Step 7: Implement the profile extraction workflow

Workflow:

1. Validate the file path.
2. Read the resume PDF text.
3. Send the full text to Gemini with a JSON-only extraction prompt.
4. Parse and validate the response.
5. Return either:
   - pretty-printed JSON, or
   - a compact summary if `output_format="summary"`

### Step 8: Add response validation

Add server-side validation for Gemini output:

- ensure valid JSON
- ensure required top-level keys exist
- coerce missing optional values to `null` or empty lists
- return MCP-friendly error text if parsing fails

## Phase 3: Multi-Resume Shortlisting

### Step 9: Add the `shortlist_candidates_for_job` MCP tool

Add a new tool:

- name: `shortlist_candidates_for_job`

Input schema:

- `job_description: str`
- `resume_files: list[str] | None = None`
- `top_k: int = 10`

Behavior:

- if `resume_files` is omitted, evaluate all PDFs in `RESUME_DIR`
- if provided, only evaluate those resumes

### Step 10: Define shortlist output structure

The tool should return structured JSON plus a readable summary.

Per candidate include:

- `file_name`
- `candidate_name`
- `recommendation`
- `match_score`
- `confidence`
- `seniority_fit`
- `matched_requirements`
- `missing_requirements`
- `notable_strengths`
- `notable_risks`
- `one_line_summary`

Allowed `recommendation` values:

- `strong_fit`
- `possible_fit`
- `reject_for_now`

### Step 11: Implement the shortlist workflow

Workflow:

1. Resolve the target resume files.
2. For each resume:
   - read the PDF
   - extract or reuse the candidate profile
   - ask Gemini to evaluate the candidate against the job description
3. Normalize each evaluation into the shortlist schema.
4. Rank by `match_score`, then by `confidence`.
5. Return:
   - top `k` candidates
   - counts by recommendation bucket
   - a readable shortlist summary

### Step 12: Optimize repeated work

Do not repeatedly re-extract resume structure during one request.

Within a single tool call:

- cache loaded resume text by file name
- cache extracted candidate profiles by file name

Keep this in-memory only for now. Do not add persistence in this phase.

### Step 13: Handle failure cases explicitly

Define behavior for:

- invalid job description
- unreadable resume file
- empty resume list
- Gemini output that is malformed
- partial failures where some resumes succeed and others fail

For partial failures:

- continue processing successful resumes
- include a `failed_resumes` section in the response

## Phase 4: Interview Pack Generation

### Step 14: Add the `generate_interview_pack` MCP tool

Add a new tool:

- name: `generate_interview_pack`

Input schema:

- `file_path: str`
- `job_description: str`
- `interview_type: str = "technical"`

Allowed `interview_type` values:

- `recruiter`
- `technical`
- `hiring_manager`

### Step 15: Define interview pack output

Return a structured object containing:

- `candidate_summary`
- `interview_focus_areas`
- `questions`
- `evaluation_signals`
- `overall_recommendation`

Each question entry should include:

- `question`
- `why_this_question`
- `target_competency`
- `strong_answer_signals`
- `weak_answer_signals`

### Step 16: Implement the interview pack workflow

Workflow:

1. Read the resume.
2. Extract or reuse the candidate profile.
3. Ask Gemini to compare the profile and job description.
4. Generate interview questions tailored to the requested interview type.
5. Return both structured content and a readable interviewer brief.

### Step 17: Keep question generation grounded

Prompt Gemini to anchor all questions in:

- explicit resume evidence
- explicit job requirements
- identified skill gaps or risks

Avoid generic questions unless the resume lacks enough evidence.

## Phase 5: Server Cleanup and Documentation

### Step 18: Update the enhanced server tool registry

The enhanced server should expose:

- `extract_skills`
- `match_resume`
- `extract_candidate_profile`
- `shortlist_candidates_for_job`
- `generate_interview_pack`

Optionally keep the legacy tools during transition. Do not remove them until the new tools are stable.

### Step 19: Fix current response issues

While implementing the new tools, fix the existing `match_resume` behavior so it returns the fully formatted response rather than only the assessment string.

### Step 20: Update docs

Update:

- root `README.md`
- `MCP/solutions/README.md`

Document:

- Gemini environment variables
- new MCP tools
- example prompts for Codex

## Testing Plan

### Step 21: Add unit-level validation coverage

Test:

- resume path validation
- JSON parsing of Gemini responses
- shortlist ranking normalization
- interview type validation
- partial failure handling

### Step 22: Add prompt contract tests

Use mocked Gemini responses to verify:

- candidate profile parsing
- shortlist schema parsing
- interview pack schema parsing

The tests should not depend on live Gemini API calls.

### Step 23: Add manual smoke-test scenarios

Run these manual scenarios from Codex after implementation:

1. Extract a candidate profile from `software-engineer-resume-example.pdf`
2. Shortlist all resumes for one backend/software-engineer job description
3. Generate a technical interview pack for the top-ranked candidate
4. Confirm malformed or missing file inputs return useful MCP error text

## Acceptance Criteria

The implementation is complete when:

- Codex can call all three new tools through the enhanced MCP server
- responses are structured, readable, and recruiter-usable
- Gemini output is validated before returning to the client
- multi-resume shortlisting works over all sample PDFs
- no repo-tracked files outside the intended server/docs/test areas are changed

## Default Decisions

These defaults should be used unless requirements change:

- Use Gemini in the enhanced server only
- Keep the basic server unchanged except for shared utility reuse if needed
- Use in-memory caching only
- Return both machine-friendly structured content and readable text
- Prefer conservative extraction over aggressive inference
