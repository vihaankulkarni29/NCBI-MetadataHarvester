# Roadmap

## Phase 0: Planning (this doc set)
- Finalize requirements, architecture, and schema

## Phase 1: MVP Backend
- FastAPI skeleton with /healthz, /jobs endpoints (in-memory store)
- Implement E-utilities adapter (httpx, retry, throttle)
- Implement free-text search -> assembly list
- Implement accession resolver (GCF/GCA and NC_)
- Implement efetch gb parsing (Biopython) for target fields
- JSON and CSV export; simple local storage
- Basic tests and CI

## Phase 2: Robustness and Scale
- Celery + Redis queue, job persistence, progress
- Caching layer; batching improvements
- Better error handling and provenance
- Auth + rate limiting per user

## Phase 3: Nice-to-haves
- Simple web UI for job submission
- Webhooks for job completion
- Enrichment: Taxonomy details, publication cross-links
- NLP keyword expansion

## Phase 4: Enterprise
- Postgres; multi-tenant auth; billing hooks
- Observability suite and SLOs
- Hardening and capacity tests
