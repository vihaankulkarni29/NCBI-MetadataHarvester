"""HTTP client with retry logic and exponential backoff."""
import asyncio
import random
from typing import Any

import httpx


class RetryableHTTPClient:
    """HTTP client with exponential backoff retry logic."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 8.0,
        timeout: float = 30.0,
        http2: bool = False,
        limits: httpx.Limits | None = None,
    ):
        """
        Initialize retryable HTTP client.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff (seconds)
            max_delay: Maximum delay between retries (seconds)
            timeout: Request timeout (seconds)
            http2: Enable HTTP/2 if supported by the server
            limits: Connection pool limits
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.timeout = timeout
        if limits is None:
            limits = httpx.Limits(max_connections=10, max_keepalive_connections=10)
        self._client = httpx.AsyncClient(timeout=timeout, http2=http2, limits=limits)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _should_retry(self, response: httpx.Response | None, exception: Exception | None) -> bool:
        """Determine if request should be retried."""
        if exception:
            # Retry on network errors, timeouts
            return isinstance(exception, (httpx.TimeoutException, httpx.NetworkError))

        if response:
            # Retry on 429 (rate limit), 5xx (server errors)
            return response.status_code == 429 or 500 <= response.status_code < 600

        return False

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter."""
        delay = min(self.base_delay * (2**attempt), self.max_delay)
        # Add jitter (±25%)
        jitter = delay * 0.25 * (2 * random.random() - 1)
        return max(0, delay + jitter)

    async def get(self, url: str, params: dict[str, Any] | None = None, **kwargs) -> httpx.Response:
        """
        GET request with retry logic.

        Args:
            url: Request URL
            params: Query parameters
            **kwargs: Additional arguments to pass to httpx

        Returns:
            Response object

        Raises:
            httpx.HTTPStatusError: On final failure after retries
        """
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.get(url, params=params, **kwargs)

                if not self._should_retry(response, None):
                    response.raise_for_status()
                    return response

                # Retry needed
                if attempt < self.max_retries:
                    delay = self._calculate_backoff(attempt)
                    await asyncio.sleep(delay)
                else:
                    response.raise_for_status()
                    return response

            except Exception as exc:
                last_exception = exc
                if not self._should_retry(None, exc):
                    raise

                if attempt < self.max_retries:
                    delay = self._calculate_backoff(attempt)
                    await asyncio.sleep(delay)
                else:
                    raise

        # Should not reach here, but satisfy type checker
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected retry loop exit")

    async def post(
        self, url: str, data: Any = None, json: Any = None, **kwargs
    ) -> httpx.Response:
        """
        POST request with retry logic.

        Args:
            url: Request URL
            data: Form data
            json: JSON body
            **kwargs: Additional arguments

        Returns:
            Response object
        """
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.post(url, data=data, json=json, **kwargs)

                if not self._should_retry(response, None):
                    response.raise_for_status()
                    return response

                if attempt < self.max_retries:
                    delay = self._calculate_backoff(attempt)
                    await asyncio.sleep(delay)
                else:
                    response.raise_for_status()
                    return response

            except Exception as exc:
                last_exception = exc
                if not self._should_retry(None, exc):
                    raise

                if attempt < self.max_retries:
                    delay = self._calculate_backoff(attempt)
                    await asyncio.sleep(delay)
                else:
                    raise

        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected retry loop exit")
