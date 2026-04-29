"""
app/pipelines/image_pipeline.py
────────────────────────────────
Image processing pipeline.

Strategy:
  1. OCR via Tesseract (local, free, primary).
  2. Gemini vision fallback when OCR confidence is low and API key is set.

Images are not resized before OCR — original resolution gives best results.
"""

from __future__ import annotations

import time
from statistics import mean

from app.adapters.base import VisionModelAdapter
from app.adapters.ocr_adapter import OcrAdapter
from app.models.domain import ExtractionMethod, ExtractionResult
from app.utils.logging_utils import get_logger

log = get_logger(__name__)

_LOW_CONFIDENCE_THRESHOLD = 0.4
_VISION_PROMPT = (
    "Extract all readable text from this image. "
    "Also describe important visual information needed for accessibility. "
    "Return structured plain text only."
)


def _image_quality_warnings(file_path: str) -> list[str]:
    warnings: list[str] = []
    try:
        from PIL import Image, ImageStat

        with Image.open(file_path) as img:
            img.load()
            gray = img.convert("L")
            stat = ImageStat.Stat(gray)
            avg = stat.mean[0] if stat.mean else 0.0
            variance = mean(stat.var) if stat.var else 0.0
            if avg < 5 or avg > 250 or variance < 2:
                warnings.append(
                    "Image appears blank or extremely low contrast; OCR quality may be poor."
                )
            if min(img.size) < 50:
                warnings.append("Image is very small; OCR may not detect text reliably.")
    except Exception as exc:
        warnings.append(f"Image quality inspection failed: {exc}")
    return warnings


class ImageProcessingPipeline:
    """Extract text from JPG/PNG images using OCR with optional vision fallback."""

    def __init__(self, vision_adapter: VisionModelAdapter | None = None) -> None:
        self._ocr = OcrAdapter()
        self._vision = vision_adapter

    def process(self, file_path: str) -> ExtractionResult:
        t0 = time.monotonic()
        quality_warnings = _image_quality_warnings(file_path)

        ocr_result = self._ocr.extract_text(file_path)
        ocr_result.warnings = quality_warnings + ocr_result.warnings

        if ocr_result.confidence >= _LOW_CONFIDENCE_THRESHOLD and ocr_result.raw_text.strip():
            log.info(
                "Image: OCR succeeded",
                extra={"confidence": ocr_result.confidence, "latency_ms": ocr_result.latency_ms},
            )
            return ocr_result

        # OCR was low-confidence or empty — try vision adapter
        if self._vision is not None:
            log.info(
                "Image: OCR low confidence (%.2f), trying vision adapter.",
                ocr_result.confidence,
            )
            vision_result = self._vision.extract_text(file_path, prompt=_VISION_PROMPT)
            if vision_result.raw_text.strip():
                combined_warnings = ocr_result.warnings + vision_result.warnings
                return ExtractionResult(
                    raw_text=vision_result.raw_text,
                    confidence=vision_result.confidence,
                    method=ExtractionMethod.VISION,
                    warnings=combined_warnings,
                    latency_ms=int((time.monotonic() - t0) * 1000),
                )

        # Return OCR result even if low-confidence, marked clearly
        warnings = list(ocr_result.warnings)
        raw = ocr_result.raw_text
        if ocr_result.confidence < _LOW_CONFIDENCE_THRESHOLD and raw.strip():
            raw = f"[LOW CONFIDENCE] {raw}"
            warnings.append(
                f"Low-confidence OCR ({ocr_result.confidence:.2f}) — text may be inaccurate."
            )
        elif not raw.strip():
            warnings.append(
                "No text could be extracted from this image. It may be blank, blurry, skewed, low contrast, or unsupported."
            )

        return ExtractionResult(
            raw_text=raw,
            confidence=ocr_result.confidence,
            method=ocr_result.method,
            warnings=warnings,
            latency_ms=int((time.monotonic() - t0) * 1000),
        )
