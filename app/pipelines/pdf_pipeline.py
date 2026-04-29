"""
app/pipelines/pdf_pipeline.py
-----------------------------
PDF processing pipeline.

Strategy (in order):
  1. Direct text extraction via PyMuPDF (fitz).
  2. Per-page OCR fallback for low-text/scanned pages.
  3. Optional vision fallback per page when OCR confidence is low.
"""

from __future__ import annotations

import time
from pathlib import Path

from app.adapters.base import VisionModelAdapter
from app.adapters.ocr_adapter import OcrAdapter
from app.config.settings import settings
from app.models.domain import ExtractionMethod, ExtractionResult
from app.utils.logging_utils import get_logger

log = get_logger(__name__)

_MIN_CHARS_PER_PAGE = 30
_LOW_CONFIDENCE_THRESHOLD = 0.4


class PDFProcessingPipeline:
    """Extract text from a PDF with direct-text -> OCR -> vision fallback."""

    def __init__(self, vision_adapter: VisionModelAdapter | None = None) -> None:
        self._ocr = OcrAdapter()
        self._vision = vision_adapter

    def process(self, file_path: str) -> ExtractionResult:
        t0 = time.monotonic()
        warnings: list[str] = []
        page_metadata: list[dict] = []

        try:
            import fitz
        except ImportError:
            return ExtractionResult(
                raw_text="",
                confidence=0.0,
                method=ExtractionMethod.UNKNOWN,
                warnings=["PyMuPDF (fitz) not installed - cannot process PDF."],
                latency_ms=int((time.monotonic() - t0) * 1000),
            )

        try:
            doc = fitz.open(file_path)
        except Exception as exc:
            return ExtractionResult(
                raw_text="",
                confidence=0.0,
                method=ExtractionMethod.UNKNOWN,
                warnings=[f"Failed to open PDF. It may be corrupt or password-protected: {exc}"],
                latency_ms=int((time.monotonic() - t0) * 1000),
            )

        all_texts: list[str] = []
        methods_used: set[str] = set()
        page_confidences: list[float] = []

        try:
            if getattr(doc, "needs_pass", False) or getattr(doc, "is_encrypted", False):
                return ExtractionResult(
                    raw_text="",
                    confidence=0.0,
                    method=ExtractionMethod.UNKNOWN,
                    warnings=["PDF is encrypted or password-protected; upload an unlocked PDF."],
                    latency_ms=int((time.monotonic() - t0) * 1000),
                )
            if doc.page_count <= 0:
                return ExtractionResult(
                    raw_text="",
                    confidence=0.0,
                    method=ExtractionMethod.UNKNOWN,
                    warnings=["PDF has zero pages or no renderable pages."],
                    latency_ms=int((time.monotonic() - t0) * 1000),
                )

            for page_num, page in enumerate(doc, start=1):
                if time.monotonic() - t0 > settings.max_processing_seconds:
                    warnings.append(
                        f"PDF processing timed out after {settings.max_processing_seconds} seconds; partial text returned."
                    )
                    break

                page_header = f"[PAGE {page_num}]"
                try:
                    direct_text = page.get_text().strip()
                except Exception as exc:
                    direct_text = ""
                    warnings.append(f"Page {page_num}: direct text extraction failed: {exc}")

                if len(direct_text) >= _MIN_CHARS_PER_PAGE:
                    all_texts.append(f"{page_header}\n{direct_text}")
                    page_confidences.append(1.0)
                    methods_used.add(ExtractionMethod.DIRECT_TEXT.value)
                    page_metadata.append(
                        {"page": page_num, "method": "direct_text", "chars": len(direct_text)}
                    )
                    continue

                img_path = Path(file_path).parent / f"_cas_page_{page_num}.png"
                try:
                    pix = page.get_pixmap(dpi=200)
                    pix.save(str(img_path))
                    ocr_result = self._ocr.extract_text(str(img_path))
                except Exception as exc:
                    warnings.append(f"Page {page_num}: rendering/OCR failed: {exc}")
                    ocr_result = ExtractionResult(
                        raw_text="",
                        confidence=0.0,
                        method=ExtractionMethod.OCR,
                        warnings=[str(exc)],
                    )
                finally:
                    img_path.unlink(missing_ok=True)

                if ocr_result.confidence >= _LOW_CONFIDENCE_THRESHOLD and ocr_result.raw_text.strip():
                    all_texts.append(f"{page_header}\n{ocr_result.raw_text}")
                    page_confidences.append(ocr_result.confidence)
                    methods_used.add(ExtractionMethod.OCR.value)
                    page_metadata.append(
                        {"page": page_num, "method": "ocr", "confidence": ocr_result.confidence}
                    )
                    warnings.extend(ocr_result.warnings)
                    continue

                if self._vision is not None:
                    img_path2 = Path(file_path).parent / f"_cas_page_vis_{page_num}.png"
                    try:
                        pix2 = page.get_pixmap(dpi=200)
                        pix2.save(str(img_path2))
                        vision_result = self._vision.extract_text(str(img_path2), prompt="")
                    except Exception as exc:
                        warnings.append(f"Page {page_num}: vision fallback failed: {exc}")
                        vision_result = ExtractionResult(
                            raw_text="",
                            confidence=0.0,
                            method=ExtractionMethod.VISION,
                            warnings=[str(exc)],
                        )
                    finally:
                        img_path2.unlink(missing_ok=True)

                    if vision_result.raw_text.strip():
                        all_texts.append(f"{page_header}\n{vision_result.raw_text}")
                        page_confidences.append(vision_result.confidence)
                        methods_used.add(ExtractionMethod.VISION.value)
                        page_metadata.append(
                            {
                                "page": page_num,
                                "method": "vision",
                                "confidence": vision_result.confidence,
                            }
                        )
                        warnings.extend(vision_result.warnings)
                        continue

                if ocr_result.raw_text.strip():
                    all_texts.append(f"{page_header}\n[LOW CONFIDENCE] {ocr_result.raw_text}")
                    page_confidences.append(ocr_result.confidence)
                    warnings.append(
                        f"Page {page_num}: low-confidence OCR ({ocr_result.confidence:.2f}) - text marked uncertain."
                    )
                else:
                    warnings.append(f"Page {page_num}: no text extracted.")

                methods_used.add(ExtractionMethod.OCR.value)
                page_metadata.append(
                    {"page": page_num, "method": "ocr_low_conf", "confidence": ocr_result.confidence}
                )
        finally:
            doc.close()

        raw_text = "\n\n".join(all_texts).strip()
        avg_confidence = (sum(page_confidences) / len(page_confidences)) if page_confidences else 0.0

        if ExtractionMethod.DIRECT_TEXT.value in methods_used:
            method = ExtractionMethod.DIRECT_TEXT
        elif ExtractionMethod.VISION.value in methods_used:
            method = ExtractionMethod.VISION
        else:
            method = ExtractionMethod.OCR

        latency = int((time.monotonic() - t0) * 1000)
        log.info(
            "PDF extraction complete",
            extra={
                "pages": len(page_metadata),
                "methods": list(methods_used),
                "confidence": round(avg_confidence, 2),
                "latency_ms": latency,
            },
        )
        return ExtractionResult(
            raw_text=raw_text,
            confidence=avg_confidence,
            method=method,
            page_metadata=page_metadata,
            warnings=warnings,
            latency_ms=latency,
        )
