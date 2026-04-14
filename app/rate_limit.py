from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after_seconds: int
    limit: int
    window_seconds: int


class InMemoryRateLimiter:
    def __init__(self, requests: int, window_seconds: int) -> None:
        self.requests = max(0, requests)
        self.window_seconds = max(1, window_seconds)
        self._buckets: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def consume(self, key: str) -> RateLimitResult:
        if self.requests <= 0:
            return RateLimitResult(
                allowed=True,
                remaining=0,
                retry_after_seconds=0,
                limit=0,
                window_seconds=self.window_seconds,
            )

        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            bucket = self._buckets.setdefault(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self.requests:
                retry_after = int(max(1, (bucket[0] + self.window_seconds) - now))
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    retry_after_seconds=retry_after,
                    limit=self.requests,
                    window_seconds=self.window_seconds,
                )

            bucket.append(now)
            remaining = max(0, self.requests - len(bucket))
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                retry_after_seconds=0,
                limit=self.requests,
                window_seconds=self.window_seconds,
            )

    def is_allowed(self, key: str) -> bool:
        return self.consume(key).allowed
