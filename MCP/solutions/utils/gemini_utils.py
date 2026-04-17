"""
Gemini utilities for recruiter-oriented resume workflows.
"""

import json
from copy import deepcopy

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - handled at runtime when dependency is missing
    genai = None


PROFILE_TEMPLATE = {
    "name": None,
    "contact": {
        "email": None,
        "phone": None,
        "linkedin": None,
    },
    "location": None,
    "current_title": None,
    "seniority_level": None,
    "estimated_years_experience": None,
    "skills": [],
    "tools_and_platforms": [],
    "programming_languages": [],
    "work_experience": [],
    "education": [],
    "projects": [],
    "certifications": [],
    "work_authorization": None,
    "summary": None,
}

SHORTLIST_TEMPLATE = {
    "candidate_name": None,
    "recommendation": "possible_fit",
    "match_score": 0,
    "confidence": "medium",
    "seniority_fit": None,
    "matched_requirements": [],
    "missing_requirements": [],
    "notable_strengths": [],
    "notable_risks": [],
    "one_line_summary": None,
}

INTERVIEW_PACK_TEMPLATE = {
    "candidate_summary": None,
    "interview_focus_areas": [],
    "questions": [],
    "evaluation_signals": [],
    "overall_recommendation": None,
}

ALLOWED_RECOMMENDATIONS = {"strong_fit", "possible_fit", "reject_for_now"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_INTERVIEW_TYPES = {"recruiter", "technical", "hiring_manager"}


def init_gemini_model(api_key, model_name):
    """Initialize the Gemini model if configuration is available."""
    if not api_key:
        return None
    if genai is None:
        return None

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def ensure_gemini_ready(model):
    """Raise a readable runtime error when Gemini is not configured."""
    if genai is None:
        raise RuntimeError(
            "Gemini SDK is not installed. Install 'google-generativeai' to use Gemini-powered tools."
        )
    if model is None:
        raise RuntimeError("Gemini is not configured. Set GEMINI_API_KEY to use Gemini-powered tools.")


def _strip_code_fences(text):
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            stripped = "\n".join(lines[1:-1]).strip()
    return stripped


def parse_json_response(raw_text):
    """Parse JSON returned by the model, tolerating markdown fences."""
    cleaned = _strip_code_fences(raw_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def generate_text(prompt, model):
    """Generate plain-text content from Gemini."""
    ensure_gemini_ready(model)
    response = model.generate_content(prompt)
    return getattr(response, "text", "").strip()


def generate_json(prompt, model):
    """Generate JSON content from Gemini and parse it."""
    ensure_gemini_ready(model)
    response = model.generate_content(prompt)
    raw_text = getattr(response, "text", "").strip()
    if not raw_text:
        raise RuntimeError("Gemini returned an empty response.")
    return parse_json_response(raw_text)


def _merge_defaults(defaults, value):
    if isinstance(defaults, dict):
        value = value if isinstance(value, dict) else {}
        merged = {}
        for key, default_value in defaults.items():
            merged[key] = _merge_defaults(default_value, value.get(key))
        for key, extra_value in value.items():
            if key not in merged:
                merged[key] = extra_value
        return merged
    if isinstance(defaults, list):
        return value if isinstance(value, list) else deepcopy(defaults)
    return defaults if value is None else value


def extract_candidate_profile_with_gemini(resume_text, file_name, model):
    prompt = f"""
You are an expert recruiting analyst.

Extract a structured candidate profile from the following resume.
Return only valid JSON matching this schema:

{json.dumps(PROFILE_TEMPLATE, indent=2)}

Rules:
- Use null when a scalar value is not explicitly present or cannot be inferred confidently.
- Use [] for missing list values.
- Do not infer protected attributes.
- Only populate work_authorization if explicitly stated.
- Keep work_experience entries concise and factual.
- summary must be a 2-3 sentence recruiter-ready summary.

Resume file: {file_name}

Resume text:
\"\"\"
{resume_text}
\"\"\"
"""
    data = generate_json(prompt, model)
    return _merge_defaults(PROFILE_TEMPLATE, data)


def evaluate_candidate_for_job(candidate_profile, job_description, model):
    prompt = f"""
You are a recruiter screening a candidate against a job description.

Return only valid JSON matching this schema:

{json.dumps(SHORTLIST_TEMPLATE, indent=2)}

Rules:
- recommendation must be one of: strong_fit, possible_fit, reject_for_now
- confidence must be one of: high, medium, low
- match_score must be an integer from 0 to 100
- matched_requirements and missing_requirements should be concrete and concise
- one_line_summary should be recruiter-friendly and evidence-based

Candidate profile JSON:
{json.dumps(candidate_profile, indent=2)}

Job description:
\"\"\"
{job_description}
\"\"\"
"""
    data = _merge_defaults(SHORTLIST_TEMPLATE, generate_json(prompt, model))
    if data["recommendation"] not in ALLOWED_RECOMMENDATIONS:
        data["recommendation"] = "possible_fit"
    if data["confidence"] not in ALLOWED_CONFIDENCE:
        data["confidence"] = "medium"
    try:
        data["match_score"] = max(0, min(100, int(data["match_score"])))
    except (TypeError, ValueError):
        data["match_score"] = 0
    return data


def generate_interview_pack_with_gemini(candidate_profile, job_description, interview_type, model):
    if interview_type not in ALLOWED_INTERVIEW_TYPES:
        raise ValueError(f"Unsupported interview_type: {interview_type}")

    prompt = f"""
You are preparing an interview pack for a hiring team.

Return only valid JSON matching this schema:

{json.dumps(INTERVIEW_PACK_TEMPLATE, indent=2)}

Rules:
- interview_focus_areas must be concrete topics derived from the candidate and role
- questions must contain 5 to 8 objects
- each question object must include:
  - question
  - why_this_question
  - target_competency
  - strong_answer_signals
  - weak_answer_signals
- strong_answer_signals and weak_answer_signals must be arrays of short bullet-like strings
- overall_recommendation must be concise and specific to the interviewer's goal

Interview type: {interview_type}

Candidate profile JSON:
{json.dumps(candidate_profile, indent=2)}

Job description:
\"\"\"
{job_description}
\"\"\"
"""
    data = _merge_defaults(INTERVIEW_PACK_TEMPLATE, generate_json(prompt, model))

    normalized_questions = []
    for item in data.get("questions", []):
        if not isinstance(item, dict):
            continue
        normalized_questions.append(
            {
                "question": item.get("question"),
                "why_this_question": item.get("why_this_question"),
                "target_competency": item.get("target_competency"),
                "strong_answer_signals": item.get("strong_answer_signals", [])
                if isinstance(item.get("strong_answer_signals"), list)
                else [],
                "weak_answer_signals": item.get("weak_answer_signals", [])
                if isinstance(item.get("weak_answer_signals"), list)
                else [],
            }
        )
    data["questions"] = normalized_questions
    return data
