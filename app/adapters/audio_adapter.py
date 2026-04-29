"""
app/adapters/audio_adapter.py
──────────────────────────────
AudioModelAdapter implementations:

  FasterWhisperAdapter — faster-whisper (local, primary)
  WhisperAdapter       — openai-whisper (local, fallback)

faster-whisper is tried first because it's smaller and faster.
If it's not installed, WhisperAdapter is used automatically.
"""

from __future__ import annotations

import time

from app.adapters.base import AudioModelAdapter
from app.config.model_registry import (
    AUDIO_PROVIDER_MODELS,
    DEFAULT_AUDIO_MODEL,
    DEFAULT_AUDIO_MODEL_SIZE,
)
from app.models.domain import ExtractionMethod, ExtractionResult
from app.utils.logging_utils import get_logger

log = get_logger(__name__)


class FasterWhisperAdapter(AudioModelAdapter):
    """Transcribe audio with faster-whisper (CTranslate2-backed)."""

    def __init__(self, model_size: str = DEFAULT_AUDIO_MODEL_SIZE) -> None:
        self._model_size = model_size
        self._model = None   # lazy-load on first call

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            log.info("Loading faster-whisper model '%s' …", self._model_size)
            self._model = WhisperModel(self._model_size, device="cpu", compute_type="int8")
        return self._model

    def transcribe(self, audio_path: str) -> ExtractionResult:
        t0 = time.monotonic()
        warnings: list[str] = []
        try:
            model = self._load()
            segments, info = model.transcribe(audio_path, beam_size=5)
            text_parts = [seg.text for seg in segments]
            raw_text = " ".join(text_parts).strip()
            avg_logprob = info.transcription_options.get("avg_logprob", None) if hasattr(info, "transcription_options") else None
            # confidence: map avg_logprob (-inf..0) to (0..1); use 0.8 if unavailable
            if avg_logprob is not None:
                import math
                confidence = max(0.0, min(1.0, math.exp(avg_logprob)))
            else:
                confidence = 0.8 if raw_text else 0.1
            if not raw_text:
                warnings.append("No speech detected in audio.")
                confidence = 0.1
        except ImportError:
            return ExtractionResult(
                raw_text="",
                confidence=0.0,
                method=ExtractionMethod.FASTER_WHISPER,
                warnings=["faster-whisper not installed."],
                latency_ms=int((time.monotonic() - t0) * 1000),
            )
        except Exception as exc:
            log.warning("faster-whisper transcription failed: %s", exc)
            return ExtractionResult(
                raw_text="",
                confidence=0.0,
                method=ExtractionMethod.FASTER_WHISPER,
                warnings=[str(exc)],
                latency_ms=int((time.monotonic() - t0) * 1000),
            )

        latency = int((time.monotonic() - t0) * 1000)
        log.info(
            "faster-whisper transcription complete",
            extra={"confidence": round(confidence, 2), "latency_ms": latency},
        )
        return ExtractionResult(
            raw_text=raw_text,
            confidence=confidence,
            method=ExtractionMethod.FASTER_WHISPER,
            warnings=warnings,
            latency_ms=latency,
        )


class WhisperAdapter(AudioModelAdapter):
    """Transcribe audio with openai-whisper."""

    def __init__(self, model_size: str = DEFAULT_AUDIO_MODEL_SIZE) -> None:
        self._model_size = model_size
        self._model = None

    def _load(self):
        if self._model is None:
            import whisper
            log.info("Loading whisper model '%s' …", self._model_size)
            self._model = whisper.load_model(self._model_size)
        return self._model

    def transcribe(self, audio_path: str) -> ExtractionResult:
        t0 = time.monotonic()
        warnings: list[str] = []
        try:
            model = self._load()
            result = model.transcribe(audio_path)
            raw_text = result.get("text", "").strip()
            confidence = 0.8 if raw_text else 0.1
            if not raw_text:
                warnings.append("No speech detected in audio.")
        except ImportError:
            return ExtractionResult(
                raw_text="",
                confidence=0.0,
                method=ExtractionMethod.WHISPER,
                warnings=["openai-whisper not installed."],
                latency_ms=int((time.monotonic() - t0) * 1000),
            )
        except Exception as exc:
            log.warning("whisper transcription failed: %s", exc)
            return ExtractionResult(
                raw_text="",
                confidence=0.0,
                method=ExtractionMethod.WHISPER,
                warnings=[str(exc)],
                latency_ms=int((time.monotonic() - t0) * 1000),
            )

        latency = int((time.monotonic() - t0) * 1000)
        log.info("whisper transcription complete", extra={"latency_ms": latency})
        return ExtractionResult(
            raw_text=raw_text,
            confidence=confidence,
            method=ExtractionMethod.WHISPER,
            warnings=warnings,
            latency_ms=latency,
        )


def build_audio_adapter(model_name: str = DEFAULT_AUDIO_MODEL) -> AudioModelAdapter:
    """Factory: return the appropriate audio adapter."""
    model_size = AUDIO_PROVIDER_MODELS.get(model_name, DEFAULT_AUDIO_MODEL_SIZE)
    if model_name == "whisper":
        return WhisperAdapter(model_size=model_size)
    return FasterWhisperAdapter(model_size=model_size)
