# Integrate NCBI‑MetadataHarvester into Your Tool (e.g., Genome Extractor)

This guide shows, step by step, how to call the Metadata Harvester from another tool to retrieve rich NCBI metadata for genomes you download (e.g., from NCBI/ENA/DDBJ).

Works great alongside a downloader like "Genome Extractor" and supports both direct Python calls and language‑agnostic HTTP API usage.

---

## What you can do

- Submit a list of accessions (e.g., CP…, NC…, NZ…, AP…, GCF_/GCA_) and get structured metadata (JSON/CSV)
- Monitor job progress and handle retries for transient failures
- Scale to large batches safely (concurrency + batched efetch under the hood)

---

## Prerequisites

- Python 3.11+ recommended
- This repository checked out locally
- Dependencies installed (from your existing setup)
- Optional but recommended: NCBI API key for higher rate limits (10 rps)

PowerShell (Windows) environment variable for the NCBI API key:

```powershell
$env:NCBI_API_KEY = "<your_api_key>"
```

---

## Step 1 — Run the Metadata Service

Start the FastAPI service locally. In a PowerShell terminal at the repo root:

```powershell
# Optional: tune concurrency and batching
$env:NCBI_CONCURRENCY = "6"
$env:NCBI_BATCH_SIZE = "20"

# Required only if you have an NCBI API key
# $env:NCBI_API_KEY = "<your_api_key>"

# Run the API server
python -m uvicorn src.ncbi_metadata_harvester.main:app --host 127.0.0.1 --port 8000
```

By default, the API is now available at: http://127.0.0.1:8000

You can verify it’s up by visiting http://127.0.0.1:8000/docs in a browser.

---

## Step 2 — Choose an integration path

You have two primary options:

1) Python client (easy if your tool is Python)
2) REST API (language‑agnostic, works from any environment)

Both call the same backend and return identical results.

---

## Option A — Python client (easiest)

We include a small, dependency‑light client at `clients/metadata_client.py` with sync and async helpers.

Use it from your tool:

```python
from clients.metadata_client import fetch_metadata_for_accessions

# Example: you already know the accession IDs
accessions = ["CP184062.1", "NC_000913.3", "AP039418.1"]

results, errors = fetch_metadata_for_accessions(accessions, base_url="http://127.0.0.1:8000", timeout=1800)
print(f"Got {len(results)} records; errors: {len(errors)}")
```

Async variant:

```python
import asyncio
from clients.metadata_client import submit_accessions, wait_for_job, get_results

async def run(accessions):
    job_id = await submit_accessions(accessions)
    status = await wait_for_job(job_id, timeout=1800)
    if status.status != "succeeded":
        raise RuntimeError(f"Job {job_id} ended with {status.status}")
    data = await get_results(job_id, format="json")
    return data["results"], data.get("errors", [])

# asyncio.run(run(["NC_000913.3"]))
```

Extract accessions from FASTA/GenBank headers you already downloaded:

```python
from clients.metadata_client import extract_accessions_from_headers, fetch_metadata_for_accessions

headers = [
    ">NC_000913.3 Escherichia coli K-12...",
    ">CP184062.1 Some E. coli strain ...",
    ">GCF_000005845.2 ASM584v2 ...",
]
accs = extract_accessions_from_headers(headers)
results, errors = fetch_metadata_for_accessions(accs)
```

Tips:
- If Genome Extractor lives in a different repo, you can vendor `clients/metadata_client.py` into it, or add this repo to PYTHONPATH.
- The client talks to the local HTTP API, so the server must be running.

---

## Option B — REST API (language‑agnostic)

Submit accessions:

```bash
# curl example (PowerShell users can use curl or Invoke-WebRequest)
curl -X POST http://127.0.0.1:8000/api/v1/jobs/accessions \
  -H "Content-Type: application/json" \
  -d '{"accessions":["NC_000913.3","CP184062.1"]}'
```

You’ll receive: `{ "job_id": "...", "status": "queued" }`

Poll status:

```bash
curl http://127.0.0.1:8000/api/v1/jobs/<job_id>
```

Fetch results (JSON or CSV):

```bash
curl "http://127.0.0.1:8000/api/v1/jobs/<job_id>/results?format=json"
# or
curl "http://127.0.0.1:8000/api/v1/jobs/<job_id>/results?format=csv"
```

Python (requests) example:

```python
import time, requests
BASE = "http://127.0.0.1:8000"

# submit
data = requests.post(f"{BASE}/api/v1/jobs/accessions", json={"accessions":["NC_000913.3","CP184062.1"]}).json()
job_id = data["job_id"]

# wait
while True:
    s = requests.get(f"{BASE}/api/v1/jobs/{job_id}").json()
    if s["status"] in {"succeeded","failed","canceled"}: break
    time.sleep(5)

# get results
res = requests.get(f"{BASE}/api/v1/jobs/{job_id}/results", params={"format":"json"}).json()
print(len(res["results"]), "records", "errors:", len(res.get("errors", [])))
```

---

## Handling failures and retries

Transient NCBI issues can cause occasional errors. You have options:

- Try again later for just the failed ones (best practice)
- Use the helper script we ship:

```powershell
# After a job completes with some errors
python src/retry_failed.py <original_job_id>
# Creates a retry job, merges successful results, and saves a merged JSON/CSV
```

You can also re‑submit the error accessions via the client or REST API.

---

## Performance and scale

- It’s safe (and fastest) to send large lists in one job; the server batches efetch internally (default 20 IDs/request) and limits concurrency (default 6).
- With an NCBI API key, the system auto‑tunes to ~10 requests/sec.
- You can override via environment variables before starting the server:

```powershell
$env:NCBI_CONCURRENCY = "8"   # try 6–8
$env:NCBI_BATCH_SIZE = "20"   # efetch IDs per request
```

Monitor long‑running jobs:

```powershell
python src/monitor_job.py <job_id>
```

---

## Minimal API reference

- POST `/api/v1/jobs/accessions`
  - Body: `{ "accessions": ["CP184062.1", "NC_000913.3", "GCF_000005845.2", ...] }`
  - Resp: `{ "job_id": "...", "status": "queued" }`

- GET `/api/v1/jobs/{job_id}`
  - Resp: `{ "status": "queued|running|succeeded|failed|canceled", "progress": { "total": N, "completed": M, "errors": E } }`

- GET `/api/v1/jobs/{job_id}/results?format=json|csv`
  - JSON: `{ "results": [...], "errors": [...] }`
  - CSV: text/csv body

---

## Common questions

- What if I only have filenames, not accessions?
  - Parse FASTA/GenBank headers to extract accessions, or maintain a filename→accession map during download. See `extract_accessions_from_headers` in the client.

- Can I combine multiple databases?
  - Yes. INSDC accessions (NCBI/ENA/DDBJ) are interoperable; RefSeq/GenBank assemblies (GCF_/GCA_) are supported.

- How do I respect NCBI limits?
  - Set `NCBI_API_KEY` to enable higher throughput. The server’s rate limiter adheres to NCBI guidance automatically.

---

## Quick smoke test

Use this to verify your integration end‑to‑end:

```python
from clients.metadata_client import fetch_metadata_for_accessions
res, errs = fetch_metadata_for_accessions(["NC_000913.3"])  # E. coli K-12 MG1655
assert len(res) == 1
print(res[0]["accession"], res[0]["organism"])
```

You’re ready to plug metadata enrichment directly into your pipeline. If you want help wiring this into a specific stage of Genome Extractor, point me to where you have the accessions or headers and I’ll drop in the adapter code.
