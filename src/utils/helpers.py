"""General-purpose helpers used across layers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_directory(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def clamp(value: int, *, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))
