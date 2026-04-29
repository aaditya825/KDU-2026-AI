"""
app/adapters/ocr_adapter.py
────────────────────────────
VisionModelAdapter implementations:

  OcrAdapter      — Tesseract OCR via pytesseract (local, free, primary)
  GeminiVisionAdapter — Google Gemini vision API (cloud, optional fallback)

The pipeline tries OcrAdapter first; if confidence is low or text is empty
it may fall through to GeminiVisionAdapter when a key is available.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path

from app.adapters.base import VisionModelAdapter
from app.config.model_registry import VISION_PROVIDER_MODELS
from app.models.domain import ExtractionMethod, ExtractionResult
from app.utils.logging_utils import get_logger

log = get_logger(__name__)

_LOW_CONFIDENCE_THRESHOLD = 60.0   # pytesseract osd confidence, out of 100


class OcrAdapter(VisionModelAdapter):
    """Extract text from an image using Tesseract OCR."""

    def extract_text(self, image_path: str, prompt: str = "") -> ExtractionResult:
        t0 = time.monotonic()
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            return ExtractionResult(
                raw_text="",
                confidence=0.0,
                method=ExtractionMethod.OCR,
                warnings=[f"pytesseract/Pillow not installed: {exc}"],
                latency_ms=0,
            )

        warnings: list[str] = []
        try:
            img = Image.open(image_path)
            raw_text: str = pytesseract.image_to_string(img)
            # Get per-word confidence data to estimate overall confidence
            data = pytesseract.image_to_data(
                img, output_type=pytesseract.Output.DICT
            )
            confs = [c for c in data["conf"] if isinstance(c, (int, float)) and c >= 0]
            avg_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.5

            if not raw_text.strip():
                warnings.append("No text detected by OCR.")
                avg_conf = 0.1

        except Exception as exc:
            log.warning("OCR extraction failed: %s", exc)
            return ExtractionResult(
                raw_text="",
                confidence=0.0,
                method=ExtractionMethod.OCR,
                warnings=[str(exc)],
                latency_ms=int((time.monotonic() - t0) * 1000),
            )

        latency = int((time.monotonic() - t0) * 1000)
        log.info(
            "OCR extraction complete",
            extra={"confidence": round(avg_conf, 2), "latency_ms": latency},
        )
        return ExtractionResult(
            raw_text=raw_text,
            confidence=avg_conf,
            method=ExtractionMethod.OCR,
            warnings=warnings,
            latency_ms=latency,
        )


class GeminiVisionAdapter(VisionModelAdapter):
    """Extract text from an image using the Gemini vision API."""

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self._api_key = api_key
        self._model = model or VISION_PROVIDER_MODELS["gemini"]

    def extract_text(self, image_path: str, prompt: str = "") -> ExtractionResult:
        t0 = time.monotonic()
        if not self._api_key:
            return ExtractionResult(
                raw_text="",
                confidence=0.0,
                method=ExtractionMethod.VISION,
                warnings=["GEMINI_API_KEY not set; skipping Gemini vision."],
            )

        try:
            from google import genai
            from PIL import Image
        except ImportError as exc:
            return ExtractionResult(
                raw_text="",
                confidence=0.0,
                method=ExtractionMethod.VISION,
                warnings=[f"google-genai/Pillow not installed: {exc}"],
            )

        try:
            client = genai.Client(api_key=self._api_key)
            img = Image.open(image_path)
            effective_prompt = prompt or (
                "Extract all readable text from this image. "
                "Also describe important visual information needed for accessibility. "
                "Return structured plain text only."
            )
            response = client.models.generate_content(
                model=self._model,
                contents=[img, effective_prompt],
            )
            raw_text = response.text or ""
            confidence = 0.85 if raw_text.strip() else 0.1
        except Exception as exc:
            log.warning("Gemini vision extraction failed: %s", exc)
            return ExtractionResult(
                raw_text="",
                confidence=0.0,
                method=ExtractionMethod.VISION,
                warnings=[str(exc)],
                latency_ms=int((time.monotonic() - t0) * 1000),
            )

        latency = int((time.monotonic() - t0) * 1000)
        log.info("Gemini vision extraction complete", extra={"latency_ms": latency})
        return ExtractionResult(
            raw_text=raw_text,
            confidence=confidence,
            method=ExtractionMethod.VISION,
            latency_ms=latency,
        )


def build_vision_adapter(provider: str, api_keys: dict[str, str]) -> VisionModelAdapter:
    """Factory: return the appropriate vision adapter based on provider name."""
    if provider == "gemini" and api_keys.get("gemini"):
        return GeminiVisionAdapter(
            api_key=api_keys["gemini"],
            model=VISION_PROVIDER_MODELS.get("gemini"),
        )
    return OcrAdapter()
