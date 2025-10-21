# Public API Design

Base URL: /api/v1
Auth: API key via header `X-API-Key: <key>` (optional in dev)

## POST /jobs/query
Submit a free-text genome metadata job.
Body:
{
  "organism": "Escherichia coli",
  "keywords": ["Antimicrobial resistance"],
  "filters": {"assembly_level": "Complete Genome", "source_db_preference": "RefSeq", "latest_only": true},
  "limit": 20
}
Response 202:
{ "job_id": "abc123", "status": "queued" }

## POST /jobs/accessions
Body:
{
  "accessions": ["GCF_000005845.2", "NC_000913.3", "GCA_000008865.1"],
  "filters": {"source_db_preference": "RefSeq", "latest_only": true}
}
Response 202: same as above

## GET /jobs/{job_id}
Response 200:
{
  "job_id": "abc123",
  "status": "running|succeeded|failed",
  "progress": {"total": 20, "completed": 12, "errors": 1},
  "submitted_at": "...",
  "updated_at": "...",
  "links": {"results_json": "/api/v1/jobs/abc123/results?format=json", "results_csv": "/api/v1/jobs/abc123/results?format=csv"}
}

## GET /jobs/{job_id}/results?format=json|csv|zip
- 200: content stream
- 404 if not ready

## GET /healthz
- 200: {status: "ok"}

## Errors
- 400: validation error details
- 401/403: auth issues
- 429: rate limit exceeded
- 500: internal error with request id

## Versioning
- Prefix with /v1; embed API version in response headers
