from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from time import time


@dataclass(slots=True)
class RateLimitWindow:
    started_at: float
    count: int


def parse_rate_limit(value: str) -> tuple[int, int]:
    amount, _, period = value.partition("/")
    if not amount or not period:
        raise ValueError("Rate limit must be in the format '<count>/<period>'.")

    max_requests = int(amount.strip())
    normalized_period = period.strip().lower()
    period_seconds = {
        "second": 1,
        "seconds": 1,
        "minute": 60,
        "minutes": 60,
        "hour": 3600,
        "hours": 3600,
    }.get(normalized_period)
    if period_seconds is None:
        raise ValueError("Unsupported rate limit period.")

    return max_requests, period_seconds


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._windows: dict[str, RateLimitWindow] = {}

    def check(self, key: str, limit: str) -> int | None:
        max_requests, window_seconds = parse_rate_limit(limit)
        now = time()
        current_window = self._windows.get(key)

        if current_window is None or now - current_window.started_at >= window_seconds:
            self._windows[key] = RateLimitWindow(started_at=now, count=1)
            return None

        if current_window.count >= max_requests:
            retry_after = ceil(window_seconds - (now - current_window.started_at))
            return max(retry_after, 1)

        current_window.count += 1
        return None
