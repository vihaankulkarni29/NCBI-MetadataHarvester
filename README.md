# NCBI-MetadataHarvester

Planning and design docs for a Python-based SaaS that extracts high-quality genome metadata from NCBI using either a free-text query (organism + keywords + filters + limit) or a user-provided accession list.

## What this will do
- Accept a query like: "Escherichia coli" AND "Antimicrobial resistance" with filter Complete Genome and limit 20
- Or accept a list of accessions (e.g., GCF_/GCA_ assemblies, NC_/NZ_/CP_ sequences)
- Fetch and normalize classic GenBank metadata fields:
	- LOCUS, DEFINITION, ACCESSION, VERSION, DBLINK (BioSample, BioProject), KEYWORDS, SOURCE, ORGANISM, REFERENCES (AUTHORS, TITLE, JOURNAL, PUBMED, REMARK)
- Return JSON and CSV, with asynchronous job handling and polite NCBI usage (rate limiting, retries, caching)

## Design docs
- docs/product-spec.md — requirements, use cases, acceptance
- docs/data-sources.md — E-utilities vs Datasets, rate limits
- docs/metadata-schema.md — JSON schema and GenBank field mapping
- docs/search-and-resolution.md — query building and accession resolution
- docs/architecture.md — SaaS architecture (FastAPI, workers, cache)
- docs/api.md — public API contract and examples
- docs/rate-limits-retries.md — throttling, batching, backoff
- docs/data-quality.md — selection rules and validation
- docs/deployment.md — deployment and operations plan
- docs/roadmap.md — phased delivery plan

## Next steps
1) Confirm requirements in product-spec.md
2) Scaffold FastAPI + worker and implement MVP search/resolve/parse per roadmap
3) Add tests and minimal CI, then iterate on scale and robustness

## Run locally
1. Create and activate a virtual environment
2. Install dependencies
3. Start the API server

PowerShell commands:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.ncbi_metadata_harvester.main:app --reload
```

Then open http://127.0.0.1:8000/healthz