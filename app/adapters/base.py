"""
app/adapters/base.py
────────────────────
Abstract base classes for all model adapters.

Concrete implementations live in sibling modules and are selected at
runtime based on .env configuration and available dependencies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.domain import ExtractionResult


class VisionModelAdapter(ABC):
    """Extract text (and optionally accessibility descriptions) from an image."""

    @abstractmethod
    def extract_text(self, image_path: str, prompt: str) -> ExtractionResult:
        ...


class AudioModelAdapter(ABC):
    """Transcribe an audio file to text."""

    @abstractmethod
    def transcribe(self, audio_path: str) -> ExtractionResult:
        ...


class LLMAdapter(ABC):
    """Generate text from a prompt."""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        ...


class EmbeddingAdapter(ABC):
    """Compute dense vector embeddings for text."""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    def embed_query(self, query: str) -> list[float]:
        ...
