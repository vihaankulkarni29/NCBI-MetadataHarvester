# System Architecture (SaaS)

## Components
- API Service (FastAPI, Python): HTTP endpoints, request validation, auth, job creation, status, results download
- Worker Queue (Celery or RQ) + Redis: background jobs for NCBI fetch/parse; progress reporting
- Cache (Redis): cache esummary/efetch responses and ID mappings
- Storage (S3/Azure Blob/GCS or local disk initially): store JSON/CSV results and logs
- Database (SQLite/PostgreSQL): persist jobs, inputs, outputs metadata, user accounts/API keys
- Rate Limiter/Middleware: per-user quotas and global throttle
- Observability: structured logging (JSON), metrics (Prometheus), tracing (optional)

## Flow
1) Client submits job (free-text or accession list)
2) API validates, enqueues background task with parameters
3) Worker processes: search/resolve -> batch efetch/esummary -> parse -> assemble metadata -> write outputs -> update job status
4) Client polls job status or receives webhook (future)
5) Client downloads results (JSON/CSV/ZIP)

## Technology Choices
- Python 3.11+
- FastAPI + Pydantic for API and schema
- Celery + Redis (or RQ + Redis) for asynchronous jobs
- httpx for HTTP with retry/backoff
- Biopython for GenBank parsing
- pandas for CSV export

## Security and Auth
- API keys/JWT for per-user access
- Secrets via environment variables/key vault
- Request-level rate limiting and quotas

## Simple Deployment (Phase 1)
- Single container: API + worker processes (2 deployments also fine)
- Redis as managed service or container
- Object storage for artifacts

## ASCII Diagram
[Client] -> [FastAPI API] -> [Redis Queue] -> [Worker(s)] -> [NCBI APIs]
                                   |                   
                                   v                   
                                [Cache]        [Object Storage]
