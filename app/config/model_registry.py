"""
Central model registry for provider/model declarations used across the app.

Keep provider names and model IDs here so adapters/services do not hardcode
them inline.
"""

from __future__ import annotations

# Embedding models
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Vision models
VISION_PROVIDER_MODELS: dict[str, str] = {
    "gemini": "gemini-2.5-flash-lite",
}
DEFAULT_VISION_PROVIDER = "ocr"

# Audio transcription models
AUDIO_PROVIDER_MODELS: dict[str, str] = {
    "faster_whisper": "base",
    "whisper": "base",
}
DEFAULT_AUDIO_MODEL = "faster_whisper"
DEFAULT_AUDIO_MODEL_SIZE = AUDIO_PROVIDER_MODELS[DEFAULT_AUDIO_MODEL]

# Provider/model input limits and app-safe guardrails.
# Provider context windows are documented limits; app-safe limits are lower
# operational limits used to keep local processing predictable.
LLM_INPUT_TOKEN_LIMITS: dict[str, int] = {
    "gemini": 1_048_576,
    "openai": 400_000,
    "local": 8_000,
}

LLM_OUTPUT_TOKEN_LIMITS: dict[str, int] = {
    "gemini": 65_536,
    "openai": 128_000,
    "local": 1_024,
}

EMBEDDING_INPUT_TOKEN_LIMITS: dict[str, int] = {
    DEFAULT_EMBEDDING_MODEL: 256,
}

DEFAULT_MAX_PDF_PAGES = 200
DEFAULT_MAX_IMAGE_PIXELS = 40_000_000
DEFAULT_MAX_QUERY_CHARS = 1_000
DEFAULT_MAX_RETRIEVAL_TOP_K = 20
DEFAULT_LLM_POSTPROCESS_INPUT_CHARS = 6_000
DEFAULT_QA_CONTEXT_CHARS = 12_000
DEFAULT_EMBEDDING_CHUNK_SIZE_CHARS = 1_000
DEFAULT_EMBEDDING_CHUNK_OVERLAP_CHARS = 200

# LLM models
LLM_PROVIDER_MODELS: dict[str, str] = {
    "gemini": "gemini-2.5-flash-lite",
    "openai": "gpt-5-mini",
    "local": "fallback",
}
DEFAULT_LLM_PROVIDER = "gemini"
DEFAULT_LLM_MODEL = LLM_PROVIDER_MODELS[DEFAULT_LLM_PROVIDER]

# Ordered fallback sequence for LLM provider selection.
LLM_FALLBACK_ORDER: list[str] = ["gemini", "openai"]

# Generation limits by task. Keep these centralized with model configuration so
# adapter callers do not hardcode token budgets.
GENERATION_MAX_TOKENS: dict[str, int] = {
    "summary": 512,
    "key_points": 512,
    "topic_tags": 256,
    "answer": 1024,
    "comparison": 512,
}
