# AGENTS.md

## Project Purpose

This repository contains a local Python MCP server for resume shortlisting. The runnable code lives in `MCP/solutions`.

There are two server entrypoints:

- `MCP/solutions/basic_resume_mcp.py`
- `MCP/solutions/langchain_resume_mcp.py`

The enhanced server is the correct place for future AI-assisted hiring workflows.

## Current Behavior

The basic server supports:

- `list_resumes`
- `read_resume`

The enhanced server currently supports:

- `extract_skills`
- `match_resume`

Shared utilities live under `MCP/solutions/utils`.

## Near-Term Product Direction

The next planned Gemini-backed features are:

1. `extract_candidate_profile`
2. `shortlist_candidates_for_job`
3. `generate_interview_pack`

These features should be added to the enhanced server, not the basic server.

## Working Rules For Agents

- Treat `MCP/solutions` as the source of truth.
- Do not add new recruiter workflows to `basic_resume_mcp.py`.
- Keep MCP tool registration and request validation in the server files.
- Move provider-specific prompting and parsing logic into utility modules under `MCP/solutions/utils`.
- Prefer structured JSON outputs internally, even if the MCP response is plain text.
- Validate model output before returning it to the MCP client.
- Use conservative extraction rules for resume data. Do not infer protected or sensitive attributes.
- Keep file path handling cross-platform with `os.path.isabs(...)`.

## Implementation Preferences

- When adding Gemini, introduce a dedicated utility module instead of mixing Gemini calls into the server file.
- Keep the enhanced server backward compatible with the current tools while new tools are being added.
- Reuse extracted resume text and candidate-profile results within a single request to avoid repeated model calls.
- Return recruiter-friendly outputs with evidence, not just scores.
- If a batch workflow partially fails, return successful results plus explicit failure details.

## Suggested File Responsibilities

- `basic_resume_mcp.py`: simple file listing and PDF text extraction only
- `langchain_resume_mcp.py`: enhanced MCP tools and orchestration
- `utils/resume_utils.py`: PDF reading and file/path helpers
- `utils/langchain_utils.py`: current LLM helper code; may be refactored or complemented by `gemini_utils.py`
- `utils/gemini_utils.py`: Gemini client, prompts, schema parsing, and response normalization

## Environment Expectations

Expected environment variables:

- `RESUME_DIR`
- `GEMINI_API_KEY` for future Gemini-backed workflows
- `GEMINI_MODEL` as an optional override

The enhanced server should continue to run as a stdio MCP server and remain compatible with Codex MCP registration.

## Quality Bar

- New tools must use Pydantic input validation.
- Model responses must be schema-checked before use.
- Error responses must be actionable and readable in an MCP client.
- Avoid hardcoding sample-resume assumptions into production logic.
- Prefer deterministic output formats over free-form prose when implementing recruiter workflows.

## Manual Validation Commands

Typical checks after implementation:

- install dependencies from `MCP/solutions/requirements.txt`
- run the enhanced server locally
- register it with Codex MCP
- call the new tools against the sample PDFs in `MCP/solutions/assets`

## Documentation Expectations

Whenever tool interfaces change, update:

- `README.md`
- `MCP/solutions/README.md`
- `plan.md` if the implementation plan materially changes
