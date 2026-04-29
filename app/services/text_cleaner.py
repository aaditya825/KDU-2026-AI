"""
app/services/text_cleaner.py
─────────────────────────────
Normalise raw extracted text before summarisation, tagging, and chunking.

Steps (in order):
  1. Decode surrogate escape sequences.
  2. Collapse excessive whitespace (tabs → space, 3+ blank lines → 2).
  3. Remove non-printable control characters (keep newlines and tabs).
  4. De-duplicate consecutive identical lines (common OCR artefact).
  5. Strip leading/trailing whitespace from each line and from the document.
"""

from __future__ import annotations

import re
import unicodedata


def clean_text(raw: str) -> str:
    """Return a normalised version of *raw* suitable for LLM input."""
    if not raw:
        return ""

    text = raw

    # 1. Normalise unicode (NFC) to merge combining characters
    text = unicodedata.normalize("NFC", text)

    # 2. Replace Windows line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Remove non-printable control characters except \n and \t
    text = re.sub(r"[^\S\n\t ]+", " ", text)   # collapse unusual whitespace
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # 4. Collapse runs of spaces on the same line
    lines = [re.sub(r" {2,}", " ", line).strip() for line in text.split("\n")]

    # 5. De-duplicate consecutive identical lines (OCR artefact)
    deduped: list[str] = []
    prev = None
    for line in lines:
        if line != prev:
            deduped.append(line)
        prev = line

    # 6. Collapse more than 2 consecutive blank lines into 2
    result_lines: list[str] = []
    blank_run = 0
    for line in deduped:
        if line == "":
            blank_run += 1
            if blank_run <= 2:
                result_lines.append(line)
        else:
            blank_run = 0
            result_lines.append(line)

    return "\n".join(result_lines).strip()
