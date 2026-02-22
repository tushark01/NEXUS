"""Token bucket rate limiter."""

from __future__ import annotations

import asyncio
import time


class TokenBucketRateLimiter:
    """Per-key token bucket rate limiter."""

    def __init__(self, rate: float, burst: int) -> None:
        """
        Args:
            rate: Tokens replenished per second.
            burst: Maximum tokens in the bucket.
        """
        self._rate = rate
        self._burst = burst
        self._buckets: dict[str, _Bucket] = {}

    def _get_bucket(self, key: str) -> _Bucket:
        if key not in self._buckets:
            self._buckets[key] = _Bucket(self._rate, self._burst)
        return self._buckets[key]

    def acquire(self, key: str = "default") -> bool:
        """Try to consume a token. Returns False if rate limited."""
        return self._get_bucket(key).consume()

    async def wait(self, key: str = "default") -> None:
        """Block until a token is available."""
        bucket = self._get_bucket(key)
        while not bucket.consume():
            await asyncio.sleep(1.0 / self._rate)


class _Bucket:
    """Internal token bucket implementation."""

    def __init__(self, rate: float, burst: int) -> None:
        self._rate = rate
        self._burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()

    def consume(self, tokens: int = 1) -> bool:
        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
        self._last_refill = now
