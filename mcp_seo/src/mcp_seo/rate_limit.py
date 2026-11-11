"""Per-token sliding-window rate limiter."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, limit_per_minute: int = 60) -> None:
        self.limit = max(1, limit_per_minute)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - 60.0
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] < window_start:
                bucket.popleft()
            if len(bucket) >= self.limit:
                return False
            bucket.append(now)
            return True


def get_rate_limiter(limit_per_minute: int) -> RateLimiter:
    return RateLimiter(limit_per_minute)
