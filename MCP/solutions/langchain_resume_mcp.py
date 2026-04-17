"""
Enhanced Resume Shortlister MCP Tool with LangChain

This tool extends the basic resume shortlister with LangChain capabilities for
resume analysis, skill extraction, and job matching.
"""

import asyncio
import json
import os
from typing import Annotated

# MCP imports
import mcp.server.stdio
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.shared.exceptions import McpError
from mcp.types import (
    TextContent,
    Tool,
    INVALID_PARAMS,
)
from pydantic import BaseModel, Field

from utils.resume_utils import read_resume, ensure_dir_exists

from utils.langchain_utils import (
    init_langchain_components,
    prepare_resume_documents,
    find_relevant_sections,
    extract_skills_with_langchain,
    assess_resume_for_job
)
from utils.gemini_utils import (
    init_gemini_model,
    extract_candidate_profile_with_gemini,
    evaluate_candidate_for_job,
    generate_interview_pack_with_gemini,
)

from dotenv import load_dotenv
load_dotenv()

# Initialize the server
server = Server("resume_shortlister_enhanced")

# Directories and configuration
RESUME_DIR = os.environ.get("RESUME_DIR", "./assets")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")

# Initialize LangChain components
embeddings, llm = init_langchain_components(OPENAI_API_KEY)
gemini_model = init_gemini_model(GEMINI_API_KEY, GEMINI_MODEL)

# Pydantic models for tool inputs
class MatchResume(BaseModel):
    file_path: Annotated[str, Field(description="Path to the resume PDF file")]
    job_description: Annotated[str, Field(description="Job description to match against")]

class ExtractSkills(BaseModel):
    file_path: Annotated[str, Field(description="Path to the resume PDF file")]

class ExtractCandidateProfile(BaseModel):
    file_path: Annotated[str, Field(description="Path to the resume PDF file")]
    output_format: Annotated[str, Field(description="json or summary")] = "json"

class ShortlistCandidatesForJob(BaseModel):
    job_description: Annotated[str, Field(description="Job description to evaluate resumes against")]
    resume_files: Annotated[list[str] | None, Field(description="Optional subset of resume PDF files")] = None
    top_k: Annotated[int, Field(description="Maximum number of ranked candidates to return", ge=1, le=100)] = 10

class GenerateInterviewPack(BaseModel):
    file_path: Annotated[str, Field(description="Path to the resume PDF file")]
    job_description: Annotated[str, Field(description="Job description to interview against")]
    interview_type: Annotated[str, Field(description="recruiter, technical, or hiring_manager")] = "technical"


def _resolve_resume_path(file_path):
    return os.path.join(RESUME_DIR, file_path) if not os.path.isabs(file_path) else file_path


def _ensure_resume_exists(file_path):
    full_path = _resolve_resume_path(file_path)
    if not os.path.exists(full_path):
        raise McpError(INVALID_PARAMS, f"Resume file not found: {file_path}")
    return full_path


def _read_resume_text(file_path):
    _ensure_resume_exists(file_path)
    resume_text = read_resume(file_path, RESUME_DIR)
    if not resume_text:
        raise McpError(INVALID_PARAMS, f"Failed to read resume: {file_path}")
    return resume_text


def _require_gemini():
    if gemini_model is None:
        raise McpError(
            INVALID_PARAMS,
            "Gemini is not configured. Install google-generativeai and set GEMINI_API_KEY.",
        )
    return gemini_model


def _list_resume_files():
    if not os.path.exists(RESUME_DIR):
        raise McpError(INVALID_PARAMS, f"Resume directory {RESUME_DIR} does not exist")
    resume_files = sorted(f for f in os.listdir(RESUME_DIR) if f.lower().endswith(".pdf"))
    if not resume_files:
        raise McpError(INVALID_PARAMS, "No resume files found in the directory")
    return resume_files


def _profile_summary(profile, file_path):
    return "\n".join(
        [
            f"Candidate Profile for '{file_path}':",
            "",
            f"Name: {profile.get('name') or 'Unknown'}",
            f"Current Title: {profile.get('current_title') or 'Unknown'}",
            f"Location: {profile.get('location') or 'Unknown'}",
            f"Seniority: {profile.get('seniority_level') or 'Unknown'}",
            f"Years Experience: {profile.get('estimated_years_experience') or 'Unknown'}",
            f"Summary: {profile.get('summary') or 'No summary available'}",
            f"Skills: {', '.join(profile.get('skills', [])) or 'None listed'}",
        ]
    )


def _format_shortlist_result(job_description, ranked_candidates, failed_resumes):
    response = [
        "Shortlist Results:",
        "",
        f"Job Description: {job_description}",
        f"Candidates Evaluated: {len(ranked_candidates)}",
        f"Candidates Failed: {len(failed_resumes)}",
        "",
    ]

    for index, candidate in enumerate(ranked_candidates, start=1):
        response.extend(
            [
                f"{index}. {candidate['candidate_name'] or candidate['file_name']}",
                f"   File: {candidate['file_name']}",
                f"   Recommendation: {candidate['recommendation']}",
                f"   Match Score: {candidate['match_score']}",
                f"   Confidence: {candidate['confidence']}",
                f"   Seniority Fit: {candidate.get('seniority_fit') or 'Unknown'}",
                f"   Summary: {candidate.get('one_line_summary') or 'No summary available'}",
            ]
        )
        if candidate.get("matched_requirements"):
            response.append(f"   Matched: {', '.join(candidate['matched_requirements'])}")
        if candidate.get("missing_requirements"):
            response.append(f"   Missing: {', '.join(candidate['missing_requirements'])}")
        response.append("")

    if failed_resumes:
        response.append("Failed Resumes:")
        for failure in failed_resumes:
            response.append(f"- {failure['file_name']}: {failure['error']}")

    return "\n".join(response).strip()


def _format_interview_pack(file_path, interview_type, pack):
    lines = [
        f"Interview Pack for '{file_path}'",
        f"Interview Type: {interview_type}",
        "",
        f"Candidate Summary: {pack.get('candidate_summary') or 'No summary available'}",
        "",
        "Focus Areas:",
    ]
    for area in pack.get("interview_focus_areas", []):
        lines.append(f"- {area}")

    lines.append("")
    lines.append("Questions:")
    for index, question in enumerate(pack.get("questions", []), start=1):
        lines.extend(
            [
                f"{index}. {question.get('question') or 'Question unavailable'}",
                f"   Why: {question.get('why_this_question') or 'Not provided'}",
                f"   Competency: {question.get('target_competency') or 'Not provided'}",
                f"   Strong Signals: {', '.join(question.get('strong_answer_signals', [])) or 'None provided'}",
                f"   Weak Signals: {', '.join(question.get('weak_answer_signals', [])) or 'None provided'}",
            ]
        )
    if pack.get("evaluation_signals"):
        lines.append("")
        lines.append("Evaluation Signals:")
        for signal in pack["evaluation_signals"]:
            lines.append(f"- {signal}")
    if pack.get("overall_recommendation"):
        lines.append("")
        lines.append(f"Overall Recommendation: {pack['overall_recommendation']}")
    return "\n".join(lines)


# MCP Tool implementation
@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="match_resume",
            description="Match a resume against a job description",
            inputSchema=MatchResume.model_json_schema(),
        ),
        Tool(
            name="extract_skills",
            description="Extract skills from a resume",
            inputSchema=ExtractSkills.model_json_schema(),
        ),
        Tool(
            name="extract_candidate_profile",
            description="Extract a structured candidate profile from a resume using Gemini",
            inputSchema=ExtractCandidateProfile.model_json_schema(),
        ),
        Tool(
            name="shortlist_candidates_for_job",
            description="Rank multiple resumes against a job description using Gemini",
            inputSchema=ShortlistCandidatesForJob.model_json_schema(),
        ),
        Tool(
            name="generate_interview_pack",
            description="Generate a tailored interview pack for a candidate using Gemini",
            inputSchema=GenerateInterviewPack.model_json_schema(),
        ),
    ]

@server.call_tool()
async def call_tool(name, arguments):
    
    if name == "match_resume":
        try:
            args = MatchResume(**arguments)
        except ValueError as e:
            raise McpError(INVALID_PARAMS, str(e))
            
        file_path = args.file_path
        job_description = args.job_description
        
        _ensure_resume_exists(file_path)
        
        filename = os.path.basename(file_path)
        
        # Step 1: Read raw text
        resume_text = _read_resume_text(file_path)
        
        # Step 2: Chunk and wrap in Documents (no embedding here)
        processed_resume = prepare_resume_documents(resume_text, filename)
        
        # Step 3: Find relevant sections using FAISS (embeddings happen here)
        relevant_sections = find_relevant_sections(processed_resume, job_description, embeddings)
        
        # Step 4: Ask LLM for assessment
        assessment = assess_resume_for_job(resume_text, job_description, llm)
        
        # Step 5: Format response
        response = f"Resume-Job Match Analysis for '{file_path}':\n\n"
        
        if relevant_sections:
            response += "LangChain identified these resume sections as most relevant to the job:\n\n"
            
            for i, (section, similarity) in enumerate(relevant_sections, 1):
                match_score = int(similarity * 100)
                response += f"Relevant Section {i} (Match: {match_score}%):\n{section}\n\n"
        
        response += "Full Assessment:\n\n"
        response += assessment
            
        return [TextContent(type="text", text=response)]
    
    elif name == "extract_skills":
        try:
            args = ExtractSkills(**arguments)
        except ValueError as e:
            raise McpError(INVALID_PARAMS, str(e))
            
        file_path = args.file_path
        
        # Check if file exists
        _ensure_resume_exists(file_path)
        
        # Read the resume
        resume_text = _read_resume_text(file_path)
        
        # Extract skills using LangChain
        skills = extract_skills_with_langchain(resume_text, llm)
        
        # Format response
        response = f"Skills Extracted from '{file_path}':\n\n"
        response += skills
            
        return [TextContent(type="text", text=response)]

    elif name == "extract_candidate_profile":
        try:
            args = ExtractCandidateProfile(**arguments)
        except ValueError as e:
            raise McpError(INVALID_PARAMS, str(e))

        output_format = args.output_format.lower()
        if output_format not in {"json", "summary"}:
            raise McpError(INVALID_PARAMS, "output_format must be 'json' or 'summary'")

        model = _require_gemini()
        resume_text = _read_resume_text(args.file_path)
        profile = extract_candidate_profile_with_gemini(
            resume_text,
            os.path.basename(args.file_path),
            model,
        )

        if output_format == "summary":
            response = _profile_summary(profile, args.file_path)
        else:
            response = json.dumps(profile, indent=2)
        return [TextContent(type="text", text=response)]

    elif name == "shortlist_candidates_for_job":
        try:
            args = ShortlistCandidatesForJob(**arguments)
        except ValueError as e:
            raise McpError(INVALID_PARAMS, str(e))

        model = _require_gemini()
        target_files = args.resume_files or _list_resume_files()
        if not target_files:
            raise McpError(INVALID_PARAMS, "No resumes provided for shortlisting")

        text_cache = {}
        profile_cache = {}
        ranked_candidates = []
        failed_resumes = []

        for file_path in target_files:
            try:
                resume_text = text_cache.setdefault(file_path, _read_resume_text(file_path))
                profile = profile_cache.setdefault(
                    file_path,
                    extract_candidate_profile_with_gemini(resume_text, os.path.basename(file_path), model),
                )
                evaluation = evaluate_candidate_for_job(profile, args.job_description, model)
                evaluation["file_name"] = file_path
                if not evaluation.get("candidate_name"):
                    evaluation["candidate_name"] = profile.get("name")
                ranked_candidates.append(evaluation)
            except Exception as exc:  # pragma: no cover - defensive batch error handling
                failed_resumes.append({"file_name": file_path, "error": str(exc)})

        ranked_candidates.sort(
            key=lambda item: (item.get("match_score", 0), {"high": 2, "medium": 1, "low": 0}.get(item.get("confidence"), 0)),
            reverse=True,
        )
        ranked_candidates = ranked_candidates[: args.top_k]

        payload = {
            "ranked_candidates": ranked_candidates,
            "failed_resumes": failed_resumes,
        }
        response = _format_shortlist_result(args.job_description, ranked_candidates, failed_resumes)
        response += "\n\nJSON:\n"
        response += json.dumps(payload, indent=2)
        return [TextContent(type="text", text=response)]

    elif name == "generate_interview_pack":
        try:
            args = GenerateInterviewPack(**arguments)
        except ValueError as e:
            raise McpError(INVALID_PARAMS, str(e))

        interview_type = args.interview_type.lower()
        if interview_type not in {"recruiter", "technical", "hiring_manager"}:
            raise McpError(INVALID_PARAMS, "interview_type must be recruiter, technical, or hiring_manager")

        model = _require_gemini()
        resume_text = _read_resume_text(args.file_path)
        profile = extract_candidate_profile_with_gemini(
            resume_text,
            os.path.basename(args.file_path),
            model,
        )
        pack = generate_interview_pack_with_gemini(profile, args.job_description, interview_type, model)
        response = _format_interview_pack(args.file_path, interview_type, pack)
        response += "\n\nJSON:\n"
        response += json.dumps(pack, indent=2)
        return [TextContent(type="text", text=response)]
    
    else:
        raise McpError(INVALID_PARAMS, f"Unknown tool: {name}")

async def main():
    """Main entry point for the MCP server."""
    try:        
        # Create resume directory if it doesn't exist
        ensure_dir_exists(RESUME_DIR)
        
        # Start the server
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="resume_shortlister_enhanced",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except Exception as e:
        raise

if __name__ == "__main__":
    asyncio.run(main())
