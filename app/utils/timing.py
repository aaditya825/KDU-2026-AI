"""
app/utils/timing.py
───────────────────
Lightweight stage-latency measurement helpers.

Usage
-----
    from app.utils.timing import Timer

    with Timer("pdf_extraction") as t:
        result = extract_pdf(path)

    print(t.elapsed_ms)   # integer milliseconds
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator


@dataclass
class Timer:
    """Context-manager that measures elapsed wall-clock time in milliseconds."""

    stage: str = "unnamed"
    _start: float = field(default=0.0, init=False, repr=False)
    _end: float = field(default=0.0, init=False, repr=False)

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_) -> None:
        self._end = time.perf_counter()

    @property
    def elapsed_ms(self) -> int:
        """Elapsed time in whole milliseconds."""
        if self._end == 0.0:
            # Still running
            return int((time.perf_counter() - self._start) * 1000)
        return int((self._end - self._start) * 1000)

    @property
    def elapsed_sec(self) -> float:
        return self.elapsed_ms / 1000.0


@contextmanager
def timed(stage: str) -> Generator[Timer, None, None]:
    """Convenience generator form of Timer."""
    t = Timer(stage=stage)
    with t:
        yield t
