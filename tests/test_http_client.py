"""Tests for HTTP client, rate limiter, and NCBI client."""
import asyncio
import time

import httpx
import pytest
from pytest import approx

from ncbi_metadata_harvester.http_client import RetryableHTTPClient
from ncbi_metadata_harvester.rate_limiter import TokenBucketRateLimiter


class TestTokenBucketRateLimiter:
    """Tests for token bucket rate limiter."""

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test that rate limiter enforces rate."""
        rate = 10.0  # 10 requests per second
        limiter = TokenBucketRateLimiter(rate=rate, burst=1)

        start = time.monotonic()
        for _ in range(5):
            await limiter.acquire()
        elapsed = time.monotonic() - start

        # Should take ~0.4s (4 waits of ~0.1s each)
        # Allow some tolerance for timing variance
        assert elapsed >= 0.3, f"Too fast: {elapsed}s"
        assert elapsed < 0.7, f"Too slow: {elapsed}s"

    @pytest.mark.asyncio
    async def test_burst_allowance(self):
        """Test that burst allows initial requests without delay."""
        rate = 5.0
        burst = 3
        limiter = TokenBucketRateLimiter(rate=rate, burst=burst)

        start = time.monotonic()
        for _ in range(3):  # First 3 should be instant (burst)
            await limiter.acquire()
        elapsed = time.monotonic() - start

        # Should be nearly instant (< 0.1s)
        assert elapsed < 0.1, f"Burst not working: {elapsed}s"


class TestRetryableHTTPClient:
    """Tests for retryable HTTP client."""

    @pytest.mark.asyncio
    async def test_successful_request(self, httpx_mock):
        """Test successful request without retry."""
        httpx_mock.add_response(url="https://example.com/test", json={"status": "ok"})

        async with RetryableHTTPClient() as client:
            resp = await client.get("https://example.com/test")
            assert resp.status_code == 200
            assert resp.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_retry_on_500(self, httpx_mock):
        """Test retry on 500 server error."""
        # First call fails, second succeeds
        httpx_mock.add_response(url="https://example.com/test", status_code=500)
        httpx_mock.add_response(url="https://example.com/test", json={"status": "ok"})

        async with RetryableHTTPClient(base_delay=0.01, max_retries=2) as client:
            resp = await client.get("https://example.com/test")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_retry_on_429(self, httpx_mock):
        """Test retry on 429 rate limit."""
        httpx_mock.add_response(url="https://example.com/test", status_code=429)
        httpx_mock.add_response(url="https://example.com/test", json={"status": "ok"})

        async with RetryableHTTPClient(base_delay=0.01, max_retries=2) as client:
            resp = await client.get("https://example.com/test")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, httpx_mock):
        """Test failure after max retries."""
        # Always return 500 (initial + max_retries attempts = 3 total)
        for _ in range(3):
            httpx_mock.add_response(url="https://example.com/test", status_code=500)

        async with RetryableHTTPClient(base_delay=0.01, max_retries=2) as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.get("https://example.com/test")

    @pytest.mark.asyncio
    async def test_no_retry_on_400(self, httpx_mock):
        """Test no retry on 4xx client errors (except 429)."""
        httpx_mock.add_response(url="https://example.com/test", status_code=400)

        async with RetryableHTTPClient(base_delay=0.01, max_retries=2) as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.get("https://example.com/test")

    @pytest.mark.asyncio
    async def test_exponential_backoff(self, httpx_mock):
        """Test exponential backoff timing."""
        # Fail twice, then succeed
        httpx_mock.add_response(url="https://example.com/test", status_code=500)
        httpx_mock.add_response(url="https://example.com/test", status_code=500)
        httpx_mock.add_response(url="https://example.com/test", json={"status": "ok"})

        base_delay = 0.1
        async with RetryableHTTPClient(base_delay=base_delay, max_retries=3) as client:
            start = time.monotonic()
            resp = await client.get("https://example.com/test")
            elapsed = time.monotonic() - start

            # Should have 2 backoffs: ~0.1s and ~0.2s (with jitter ±25%)
            # Minimum: ~0.225s (0.075 + 0.15), allow some tolerance
            assert elapsed >= 0.15, f"Backoff too short: {elapsed}s"
            assert resp.status_code == 200
