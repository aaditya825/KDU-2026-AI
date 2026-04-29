"""
app/pipelines/content_router.py
────────────────────────────────
Routes a FileMetadata record to the correct processing pipeline.

Phase 2: PDFProcessingPipeline, ImageProcessingPipeline, AudioProcessingPipeline
are now fully wired. Vision and audio adapters are built from settings.
"""

from __future__ import annotations

from app.config.settings import settings
from app.models.domain import FileMetadata, FileType
from app.utils.logging_utils import get_logger

log = get_logger(__name__)


class ContentRouter:
    """Resolves and returns the appropriate pipeline instance for a file type."""

    def get_pipeline(self, meta: FileMetadata):
        """Return the correct pipeline for *meta.file_type*."""
        log.debug("Routing file", extra={"file_type": meta.file_type.value})

        api_keys = {
            "gemini": settings.gemini_api_key,
            "openai": settings.openai_api_key,
        }

        if meta.file_type == FileType.PDF:
            from app.adapters.ocr_adapter import build_vision_adapter
            from app.pipelines.pdf_pipeline import PDFProcessingPipeline

            vision = None
            if not settings.local_only and settings.default_vision_provider != "ocr":
                vision = build_vision_adapter(settings.default_vision_provider, api_keys)
            return PDFProcessingPipeline(vision_adapter=vision)

        if meta.file_type == FileType.IMAGE:
            from app.adapters.ocr_adapter import build_vision_adapter
            from app.pipelines.image_pipeline import ImageProcessingPipeline

            vision = None
            if not settings.local_only and settings.default_vision_provider != "ocr":
                vision = build_vision_adapter(settings.default_vision_provider, api_keys)
            return ImageProcessingPipeline(vision_adapter=vision)

        if meta.file_type == FileType.AUDIO:
            from app.adapters.audio_adapter import build_audio_adapter
            from app.pipelines.audio_pipeline import AudioProcessingPipeline

            audio = build_audio_adapter(settings.default_audio_model)
            return AudioProcessingPipeline(audio_adapter=audio)

        raise ValueError(f"Unknown file type: {meta.file_type}")
