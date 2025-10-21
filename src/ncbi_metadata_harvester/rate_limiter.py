"""Rate limiting utilities."""
import asyncio
import time
from collections import deque


class TokenBucketRateLimiter:
    """Token bucket rate limiter for async requests."""

    def __init__(self, rate: float, burst: int = 1):
        """
        Initialize rate limiter.

        Args:
            rate: Requests per second allowed
            burst: Maximum burst size (tokens that can accumulate)
        """
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a token is available, then consume it."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
                self.last_update = time.monotonic()
            else:
                self.tokens -= 1.0


class SlidingWindowRateLimiter:
    """Sliding window rate limiter (simple deque-based implementation)."""

    def __init__(self, rate: float):
        """
        Initialize rate limiter.

        Args:
            rate: Requests per second allowed
        """
        self.rate = rate
        self.window = 1.0  # 1 second window
        self.requests: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a slot is available in the sliding window."""
        async with self._lock:
            now = time.monotonic()
            # Remove requests outside the window
            cutoff = now - self.window
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()

            # If at capacity, wait until oldest request expires
            if len(self.requests) >= self.rate:
                wait_time = self.requests[0] + self.window - now
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    now = time.monotonic()
                    # Clean up again after sleep
                    cutoff = now - self.window
                    while self.requests and self.requests[0] < cutoff:
                        self.requests.popleft()

            self.requests.append(now)
