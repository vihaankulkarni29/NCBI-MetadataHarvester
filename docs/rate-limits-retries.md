# Rate Limiting, Batching, and Retries

## NCBI Politeness
- Default throttle: up to 3 req/s without API key; up to 10 req/s with API key
- Add tool and email parameters to calls
- Use ID list batching: esummary/efetch can accept many IDs (e.g., up to ~200)

## Client-Side Controls
- Token bucket limiter per-destination host
- Per-user quota in API
- Exponential backoff (e.g., 0.5s, 1s, 2s, 4s, jitter) for 429/5xx
- Circuit breaker to avoid hammering during outages

## Caching Strategy
- Cache esearch/esummary results for hours to days
- Cache accession->assembly/nuccore link mappings
- ETag/Last-Modified support if available

## Batch Sizes
- esummary/efetch IDs: tune 50-100 IDs per call to balance payload vs rate

## Observability
- Log request/response metadata (status, duration, retries)
- Emit metrics: requests, errors, retries, cache hit rate
