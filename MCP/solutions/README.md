# Codex Setup

`MCP/solutions` contains the runnable MCP servers.

## Servers

- `basic_resume_mcp.py`: lists resume PDFs and extracts raw text
- `langchain_resume_mcp.py`: extracts skills and matches resumes to job descriptions

## Requirements

```bash
pip install -r requirements.txt
```

Set:

- `RESUME_DIR`
- `OPENAI_API_KEY` for `langchain_resume_mcp.py`
- `GEMINI_API_KEY` for the Gemini-powered recruiter tools
- `GEMINI_MODEL` as an optional override

## Add to Codex

From the repository root:

```bash
codex.cmd mcp add resume-shortlister --env RESUME_DIR=./MCP/solutions/assets -- python MCP/solutions/basic_resume_mcp.py
```

```bash
codex.cmd mcp add resume-shortlister-enhanced --env RESUME_DIR=./MCP/solutions/assets --env OPENAI_API_KEY=your-openai-api-key --env GEMINI_API_KEY=your-gemini-api-key -- python MCP/solutions/langchain_resume_mcp.py
```

Check registered servers:

```bash
codex.cmd mcp list
```

## Notes

- The MCP transport is stdio, which Codex supports directly.
- Absolute path handling now uses `os.path.isabs(...)`, so Windows paths work correctly.

## Available Enhanced Tools

- `extract_skills`
- `match_resume`
- `extract_candidate_profile`
- `shortlist_candidates_for_job`
- `generate_interview_pack`
