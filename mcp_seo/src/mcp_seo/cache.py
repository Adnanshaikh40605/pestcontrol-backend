"""Simple in-process TTL cache."""

from __future__ import annotations

import threading
import time
from typing import Any


class TtlCache:
    def __init__(self) -> None:
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            expires_at, value = item
            if expires_at < time.monotonic():
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        with self._lock:
            self._data[key] = (time.monotonic() + max(1, ttl_seconds), value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


CACHE = TtlCache()
