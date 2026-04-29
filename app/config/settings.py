"""
app/config/settings.py
──────────────────────
Configuration loader.

Reads values from the environment (populated via .env through python-dotenv).
All settings have safe defaults so the system works out-of-the-box in local-only
mode without any .env file present.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from app.config.model_registry import (
    DEFAULT_AUDIO_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_MAX_IMAGE_PIXELS,
    DEFAULT_MAX_AUDIO_TRANSCRIPTION_SECONDS,
    DEFAULT_MAX_OCR_SECONDS,
    DEFAULT_MAX_PATH_CHARS,
    DEFAULT_MAX_PDF_PAGES,
    DEFAULT_MAX_PROCESSING_SECONDS,
    DEFAULT_MAX_QUERY_CHARS,
    DEFAULT_MAX_RETRIEVAL_TOP_K,
    DEFAULT_VISION_PROVIDER,
)

# Load .env from project root (or wherever the process is started from).
# Does nothing if no .env file exists — env vars set externally are used as-is.
load_dotenv(dotenv_path=Path(".env"), override=False)


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key, str(default)).strip().lower()
    return val in ("1", "true", "yes", "on")


# ─────────────────────────────────────────────
# Settings dataclass
# ─────────────────────────────────────────────

@dataclass
class Settings:
    # ── Paths ──
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", "data")))
    sqlite_db_path: Path = field(
        default_factory=lambda: Path(_env("SQLITE_DB_PATH", "data/sqlite/cas.db"))
    )

    # ── Upload limits ──
    max_upload_mb: int = field(default_factory=lambda: _env_int("MAX_UPLOAD_MB", 25))
    max_audio_duration_sec: int = field(
        default_factory=lambda: _env_int("MAX_AUDIO_DURATION_SEC", 600)
    )
    max_pdf_pages: int = field(
        default_factory=lambda: _env_int("MAX_PDF_PAGES", DEFAULT_MAX_PDF_PAGES)
    )
    max_image_pixels: int = field(
        default_factory=lambda: _env_int("MAX_IMAGE_PIXELS", DEFAULT_MAX_IMAGE_PIXELS)
    )
    max_query_chars: int = field(
        default_factory=lambda: _env_int("MAX_QUERY_CHARS", DEFAULT_MAX_QUERY_CHARS)
    )
    max_retrieval_top_k: int = field(
        default_factory=lambda: _env_int("MAX_RETRIEVAL_TOP_K", DEFAULT_MAX_RETRIEVAL_TOP_K)
    )
    max_processing_seconds: int = field(
        default_factory=lambda: _env_int("MAX_PROCESSING_SECONDS", DEFAULT_MAX_PROCESSING_SECONDS)
    )
    max_ocr_seconds: int = field(
        default_factory=lambda: _env_int("MAX_OCR_SECONDS", DEFAULT_MAX_OCR_SECONDS)
    )
    max_audio_transcription_seconds: int = field(
        default_factory=lambda: _env_int(
            "MAX_AUDIO_TRANSCRIPTION_SECONDS",
            DEFAULT_MAX_AUDIO_TRANSCRIPTION_SECONDS,
        )
    )
    max_path_chars: int = field(
        default_factory=lambda: _env_int("MAX_PATH_CHARS", DEFAULT_MAX_PATH_CHARS)
    )

    # ── Model defaults ──
    default_vector_store: str = field(
        default_factory=lambda: _env("DEFAULT_VECTOR_STORE", "chroma")
    )
    default_embedding_model: str = field(
        default_factory=lambda: _env("DEFAULT_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    )
    default_llm_provider: str = field(
        default_factory=lambda: _env("DEFAULT_LLM_PROVIDER", DEFAULT_LLM_PROVIDER)
    )
    default_llm_model: str = field(
        default_factory=lambda: _env("DEFAULT_LLM_MODEL", DEFAULT_LLM_MODEL)
    )
    default_vision_provider: str = field(
        default_factory=lambda: _env("DEFAULT_VISION_PROVIDER", DEFAULT_VISION_PROVIDER)
    )
    default_audio_model: str = field(
        default_factory=lambda: _env("DEFAULT_AUDIO_MODEL", DEFAULT_AUDIO_MODEL)
    )

    # ── Behaviour flags ──
    local_only: bool = field(default_factory=lambda: _env_bool("LOCAL_ONLY", False))
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))

    # ── API keys (never logged) ──
    gemini_api_key: str = field(default_factory=lambda: _env("GEMINI_API_KEY", ""))
    openai_api_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY", ""))

    # ── Derived paths ──
    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def vector_db_dir(self) -> Path:
        return self.data_dir / "vector_db"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def ensure_dirs(self) -> None:
        """Create required data directories if they do not exist."""
        for d in (
            self.uploads_dir,
            self.processed_dir,
            self.vector_db_dir,
            self.sqlite_db_path.parent,
        ):
            d.mkdir(parents=True, exist_ok=True)

    def configure_logging(self) -> None:
        level = getattr(logging, self.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )


# ── Module-level singleton ──
settings = Settings()
