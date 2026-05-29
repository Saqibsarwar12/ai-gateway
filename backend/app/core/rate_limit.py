"""Rate limiting using in-memory sliding window (no Redis required on Free tier)."""
import time
from collections import defaultdict
from typing import Optional
import asyncio


class RateLimiter:
    """In-memory sliding window rate limiter. Works without Redis on Free tier."""

    def __init__(self):
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.time()
        window_start = now - window_seconds

        async with self._lock:
            # Remove old entries
            self._windows[key] = [t for t in self._windows[key] if t > window_start]

            if len(self._windows[key]) < limit:
                self._windows[key].append(now)
                return True
            return False

    async def get_remaining(self, key: str, limit: int, window_seconds: int = 60) -> int:
        now = time.time()
        window_start = now - window_seconds
        async with self._lock:
            self._windows[key] = [t for t in self._windows[key] if t > window_start]
            return max(0, limit - len(self._windows[key]))


# Global limiter instance
rate_limiter = RateLimiter()
