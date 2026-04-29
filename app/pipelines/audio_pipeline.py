"""
app/pipelines/audio_pipeline.py
────────────────────────────────
Audio processing pipeline.

Strategy:
  1. faster-whisper (local, primary, int8 quantised for CPU speed).
  2. openai-whisper fallback if faster-whisper is not installed.

Audio is not normalised before transcription — whisper handles variable
loudness internally.
"""

from __future__ import annotations

import time

from app.adapters.audio_adapter import FasterWhisperAdapter, WhisperAdapter
from app.adapters.base import AudioModelAdapter
from app.config.model_registry import AUDIO_PROVIDER_MODELS, DEFAULT_AUDIO_MODEL_SIZE
from app.models.domain import ExtractionMethod, ExtractionResult
from app.utils.logging_utils import get_logger

log = get_logger(__name__)


class AudioProcessingPipeline:
    """Transcribe MP3/WAV audio files to text."""

    def __init__(self, audio_adapter: AudioModelAdapter | None = None) -> None:
        self._adapter = audio_adapter or self._default_adapter()

    @staticmethod
    def _default_adapter() -> AudioModelAdapter:
        model_size = AUDIO_PROVIDER_MODELS.get("faster_whisper", DEFAULT_AUDIO_MODEL_SIZE)
        try:
            import faster_whisper  # noqa: F401
            return FasterWhisperAdapter(model_size=model_size)
        except ImportError:
            log.warning("faster-whisper not found; falling back to openai-whisper.")
            fallback_size = AUDIO_PROVIDER_MODELS.get("whisper", DEFAULT_AUDIO_MODEL_SIZE)
            return WhisperAdapter(model_size=fallback_size)

    def process(self, file_path: str) -> ExtractionResult:
        t0 = time.monotonic()
        result = self._adapter.transcribe(file_path)
        total_latency = int((time.monotonic() - t0) * 1000)

        log.info(
            "Audio pipeline complete",
            extra={
                "method": result.method.value,
                "confidence": round(result.confidence, 2),
                "latency_ms": total_latency,
            },
        )
        return ExtractionResult(
            raw_text=result.raw_text,
            confidence=result.confidence,
            method=result.method,
            warnings=result.warnings,
            latency_ms=total_latency,
        )
