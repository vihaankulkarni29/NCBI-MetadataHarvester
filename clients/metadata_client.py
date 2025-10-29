"""Lightweight Python client for NCBI-MetadataHarvester.

Use from other projects (e.g., Genome Extractor) to fetch metadata for a list of accessions.

Quickstart:

    from clients.metadata_client import fetch_metadata_for_accessions
    results = fetch_metadata_for_accessions(["CP184062.1", "NC_000913.3"])  # blocking helper
    print(len(results), "records")

This module provides both async and sync helpers.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Iterable, Literal, Optional

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


@dataclass(frozen=True)
class JobProgress:
    total: int
    completed: int
    errors: int


@dataclass(frozen=True)
class JobStatus:
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed", "canceled"]
    progress: JobProgress


class MetadataClientError(Exception):
    pass


async def submit_accessions(
    accessions: Iterable[str],
    *,
    base_url: str = DEFAULT_BASE_URL,
    client: Optional[httpx.AsyncClient] = None,
) -> str:
    """Submit a job for a list of accessions. Returns job_id."""
    owns = False
    if client is None:
        client = httpx.AsyncClient(timeout=300.0)
        owns = True
    try:
        payload = {"accessions": list(accessions)}
        resp = await client.post(f"{base_url}/api/v1/jobs/accessions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["job_id"]
    finally:
        if owns:
            await client.aclose()


async def get_job_status(
    job_id: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    client: Optional[httpx.AsyncClient] = None,
) -> JobStatus:
    owns = False
    if client is None:
        client = httpx.AsyncClient(timeout=60.0)
        owns = True
    try:
        resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}")
        resp.raise_for_status()
        data = resp.json()
        prog = data.get("progress") or {"total": 0, "completed": 0, "errors": 0}
        return JobStatus(
            job_id=job_id,
            status=data["status"],
            progress=JobProgress(total=prog.get("total", 0), completed=prog.get("completed", 0), errors=prog.get("errors", 0)),
        )
    finally:
        if owns:
            await client.aclose()


async def wait_for_job(
    job_id: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    poll_interval: float = 5.0,
    timeout: float = 1800.0,
    client: Optional[httpx.AsyncClient] = None,
) -> JobStatus:
    """Poll until job completes or times out."""
    owns = False
    if client is None:
        client = httpx.AsyncClient(timeout=60.0)
        owns = True
    try:
        deadline = asyncio.get_event_loop().time() + timeout
        last_status: Optional[JobStatus] = None
        while True:
            status = await get_job_status(job_id, base_url=base_url, client=client)
            last_status = status
            if status.status in {"succeeded", "failed", "canceled"}:
                return status
            if asyncio.get_event_loop().time() > deadline:
                raise MetadataClientError(f"Timeout waiting for job {job_id}: {status.status}")
            await asyncio.sleep(poll_interval)
    finally:
        if owns:
            await client.aclose()


async def get_results(
    job_id: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    format: Literal["json", "csv"] = "json",
    client: Optional[httpx.AsyncClient] = None,
):
    owns = False
    if client is None:
        client = httpx.AsyncClient(timeout=300.0)
        owns = True
    try:
        resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}/results", params={"format": format})
        resp.raise_for_status()
        if format == "json":
            return resp.json()
        return resp.text
    finally:
        if owns:
            await client.aclose()


def fetch_metadata_for_accessions(
    accessions: Iterable[str],
    *,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = 1800.0,
):
    """Blocking helper: submit, wait, and return JSON results['results'] list.

    Raises MetadataClientError on failure or timeout.
    """
    async def _run():
        async with httpx.AsyncClient(timeout=300.0) as client:
            job_id = await submit_accessions(accessions, base_url=base_url, client=client)
            status = await wait_for_job(job_id, base_url=base_url, timeout=timeout, client=client)
            if status.status != "succeeded":
                raise MetadataClientError(f"Job {job_id} finished with status {status.status}")
            data = await get_results(job_id, base_url=base_url, format="json", client=client)
            return data["results"], data.get("errors", [])

    return asyncio.run(_run())


# Optional helper: extract accession from FASTA/GenBank headers
import re

ACC_RE = re.compile(r"\b([A-Z]{1,4}_?\d{3,9}(?:\.\d+)?)\b")


def extract_accessions_from_headers(headers: Iterable[str]) -> list[str]:
    """Best-effort extraction of INSDC-style accessions from header lines.

    Works for e.g.,
      ">NC_000913.3 Escherichia coli..."
      ">CP184062.1 ..."
      ">GCF_000005845.2 ..."
    """
    accs: list[str] = []
    for h in headers:
        m = ACC_RE.search(h)
        if m:
            accs.append(m.group(1))
    return accs
