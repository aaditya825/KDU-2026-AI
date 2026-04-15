"""Configuration contracts and loading helpers."""

from src.core.config.constants import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_FINAL_TOP_K,
    DEFAULT_FUSED_TOP_K,
    DEFAULT_KEYWORD_TOP_K,
    DEFAULT_SEMANTIC_TOP_K,
)
from src.core.config.settings import AppSettings, load_settings

__all__ = [
    "AppSettings",
    "DEFAULT_CHUNK_OVERLAP",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_FINAL_TOP_K",
    "DEFAULT_FUSED_TOP_K",
    "DEFAULT_KEYWORD_TOP_K",
    "DEFAULT_SEMANTIC_TOP_K",
    "load_settings",
]
