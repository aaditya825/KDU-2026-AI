"""Simple timing utilities for later pipeline instrumentation."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import Iterator


@dataclass(slots=True)
class Timer:
    start_time: float
    end_time: float | None = None

    @property
    def elapsed_ms(self) -> float:
        end_time = self.end_time if self.end_time is not None else perf_counter()
        return (end_time - self.start_time) * 1000.0


@contextmanager
def timed() -> Iterator[Timer]:
    timer = Timer(start_time=perf_counter())
    try:
        yield timer
    finally:
        timer.end_time = perf_counter()
