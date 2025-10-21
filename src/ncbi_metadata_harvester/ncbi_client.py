"""NCBI E-utilities client with rate limiting and retry."""
from typing import Any

import httpx

from .config import get_settings
from .http_client import RetryableHTTPClient
from .rate_limiter import TokenBucketRateLimiter


class NCBIClient:
    """Client for NCBI E-utilities API with rate limiting and retry."""

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self):
        """Initialize NCBI client with settings-based configuration."""
        self.settings = get_settings()
        # Determine effective rate limit: prefer 10 rps when API key is present
        effective_rate = self.settings.ncbi_rate_limit
        if self.settings.ncbi_api_key and effective_rate <= 3.0:
            effective_rate = 10.0
        burst = max(1, getattr(self.settings, "ncbi_concurrency", 6))
        self.rate_limiter = TokenBucketRateLimiter(rate=effective_rate, burst=burst)
        limits = httpx.Limits(
            max_connections=self.settings.http_max_connections,
            max_keepalive_connections=self.settings.http_max_keepalive,
        )
        self.http_client = RetryableHTTPClient(
            max_retries=self.settings.max_retries,
            base_delay=self.settings.retry_base_delay,
            max_delay=self.settings.retry_max_delay,
            timeout=30.0,
            http2=self.settings.http2_enabled,
            limits=limits,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.http_client.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _build_params(self, **kwargs: Any) -> dict[str, Any]:
        """Build request parameters with tool/email/api_key."""
        params = {
            "tool": self.settings.ncbi_tool,
            "email": self.settings.ncbi_email,
        }
        if self.settings.ncbi_api_key:
            params["api_key"] = self.settings.ncbi_api_key
        params.update(kwargs)
        return params

    async def esearch(
        self, db: str, term: str, retmax: int = 20, **kwargs: Any
    ) -> httpx.Response:
        """
        Execute ESearch query.

        Args:
            db: Database to search (e.g., 'assembly', 'nuccore')
            term: Search term
            retmax: Maximum results to return
            **kwargs: Additional query parameters

        Returns:
            Response object with search results
        """
        await self.rate_limiter.acquire()
        params = self._build_params(db=db, term=term, retmax=retmax, retmode="json", **kwargs)
        url = f"{self.BASE_URL}/esearch.fcgi"
        return await self.http_client.get(url, params=params)

    async def esummary(self, db: str, id: str | list[str], **kwargs: Any) -> httpx.Response:
        """
        Execute ESummary query.

        Args:
            db: Database (e.g., 'assembly', 'nuccore')
            id: Single ID or list of IDs
            **kwargs: Additional query parameters

        Returns:
            Response object with summaries
        """
        await self.rate_limiter.acquire()
        id_str = ",".join(id) if isinstance(id, list) else id
        params = self._build_params(db=db, id=id_str, retmode="json", **kwargs)
        url = f"{self.BASE_URL}/esummary.fcgi"
        return await self.http_client.get(url, params=params)

    async def efetch(
        self, db: str, id: str | list[str], rettype: str = "gb", retmode: str = "text", **kwargs: Any
    ) -> httpx.Response:
        """
        Execute EFetch query.

        Args:
            db: Database (e.g., 'nuccore')
            id: Single ID or list of IDs
            rettype: Return type (e.g., 'gb', 'fasta')
            retmode: Return mode ('text', 'xml')
            **kwargs: Additional query parameters

        Returns:
            Response object with record data
        """
        await self.rate_limiter.acquire()
        id_str = ",".join(id) if isinstance(id, list) else id
        params = self._build_params(db=db, id=id_str, rettype=rettype, retmode=retmode, **kwargs)
        url = f"{self.BASE_URL}/efetch.fcgi"
        return await self.http_client.get(url, params=params)

    async def elink(
        self, dbfrom: str, db: str, id: str | list[str], linkname: str | None = None, **kwargs: Any
    ) -> httpx.Response:
        """
        Execute ELink query.

        Args:
            dbfrom: Source database
            db: Target database
            id: Single ID or list of IDs
            linkname: Link name filter (e.g., 'assembly_nuccore_refseq')
            **kwargs: Additional query parameters

        Returns:
            Response object with links
        """
        await self.rate_limiter.acquire()
        id_str = ",".join(id) if isinstance(id, list) else id
        params = self._build_params(dbfrom=dbfrom, db=db, id=id_str, retmode="json", **kwargs)
        if linkname:
            params["linkname"] = linkname
        url = f"{self.BASE_URL}/elink.fcgi"
        return await self.http_client.get(url, params=params)
