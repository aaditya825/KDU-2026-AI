# Resume Shortlister MCP

This repository contains a Python MCP server for resume shortlisting.

The runnable implementation is in `MCP/solutions`. It already uses the standard
Python MCP SDK over stdio, so it can be used from Codex without a protocol
rewrite.

## What changed for Codex

- The runnable solution is now documented for Codex usage.
- Windows path handling was fixed to support absolute paths correctly.
- `python-dotenv` was added to the requirements because the enhanced server
  imports it.

## Run the server locally

Install dependencies:

```bash
pip install -r MCP/solutions/requirements.txt
```

Basic server:

```bash
python MCP/solutions/basic_resume_mcp.py
```

Enhanced server:

```bash
python MCP/solutions/langchain_resume_mcp.py
```

Environment variables:

- `RESUME_DIR`: directory containing resume PDFs
- `OPENAI_API_KEY`: required for the enhanced LangChain server
- `GEMINI_API_KEY`: required for the Gemini-powered recruiter tools
- `GEMINI_MODEL`: optional Gemini model override for the enhanced server

## Add the server to Codex

Codex can launch the local stdio server directly.

Basic server:

```bash
codex.cmd mcp add resume-shortlister --env RESUME_DIR=./MCP/solutions/assets -- python MCP/solutions/basic_resume_mcp.py
```

Enhanced server:

```bash
codex.cmd mcp add resume-shortlister-enhanced --env RESUME_DIR=./MCP/solutions/assets --env OPENAI_API_KEY=your-openai-api-key --env GEMINI_API_KEY=your-gemini-api-key -- python MCP/solutions/langchain_resume_mcp.py
```

Verify:

```bash
codex.cmd mcp list
```

## Project layout

- `MCP/solutions`: implemented MCP servers and utilities

## Enhanced tools

The enhanced MCP server now exposes:

- `extract_skills`
- `match_resume`
- `extract_candidate_profile`
- `shortlist_candidates_for_job`
- `generate_interview_pack`
