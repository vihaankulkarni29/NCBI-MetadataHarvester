# Product Specification: NCBI Metadata Harvester

## Summary
A Python-based SaaS that retrieves high-quality genome metadata from NCBI given either (a) a structured free-text query (organism + keywords + filters + max count) or (b) a list of accessions. It returns normalized metadata in JSON/CSV and supports asynchronous jobs, batching, retries, and polite NCBI usage.

## Primary Use Cases
- Free-text genome query
  - Input: organism name (e.g., "Escherichia coli"), keywords (e.g., "Antimicrobial resistance"), filters (e.g., complete genome), and a max N
  - Output: Up to N genome metadata records aggregated from NCBI (Assembly + Nuccore + BioSample + BioProject)
- Accession list enrichment
  - Input: list of accessions (e.g., GCF_/GCA_ assemblies, NC_/NZ_/CP/CM/CH sequence accessions)
  - Output: Metadata for each, resolved to the appropriate assembly and representative sequence(s)

## Users and Personas
- Bioinformaticians and researchers needing standardized metadata for comparative genomics
- Lab/institutional data teams maintaining curated datasets
- Software systems integrating genome metadata into pipelines

## Inputs
- Free-text mode body:
  - organism: string (required)
  - keywords: array[string] or string (optional)
  - filters: object
    - assembly_level: ["Complete Genome", "Chromosome", "Scaffold", "Contig"] (default: any; recommended default: Complete Genome)
    - source_db_preference: ["RefSeq", "GenBank", "Either"] (default: RefSeq)
    - latest_only: boolean (default: true)
  - limit: integer (default: 20, max configurable)
- Accession list mode body:
  - accessions: array[string] (required)
  - same filters as above (optional)

## Outputs
- JSON: Array of normalized metadata objects, one per genome (see Schema). Multi-reference fields are arrays.
- CSV: Flattened view with key fields; multi-valued fields aggregated (e.g., semicolon-delimited) or exported to a secondary CSV for references.
- Optionally a ZIP containing JSON + CSV + provenance logs.

## Core Requirements
- Accurate metadata mapping to classic GenBank fields:
  - LOCUS, DEFINITION, ACCESSION, VERSION, DBLINK (BioSample, BioProject), KEYWORDS, SOURCE, ORGANISM, REFERENCE (AUTHORS, TITLE, JOURNAL, PUBMED, REMARK)
- Querying by organism + keywords + filters and limiting results
- Robust accession resolution (GCF/GCA vs NC_/NZ_/CP/CM/etc.)
- Prefer RefSeq (GCF) and latest version; deduplicate assemblies
- Respect NCBI policies: throttle, backoff, email/tool params, API key support
- Asynchronous job handling with progress status and downloadable results
- Observability: structured logs, request IDs, basic metrics

## Non-Goals (initial)
- Downloading full sequence FASTA/GBFF as a deliverable (we only parse for metadata)
- UI-heavy web frontend (start with simple API + minimal console/front)
- Sophisticated ontology expansion for keywords (basic keyword matching only, future NLP possible)

## Acceptance Criteria
- Given a query "Escherichia coli" + keyword "Antimicrobial resistance" with filter complete genome and limit 20, the system returns up to 20 normalized metadata records with the requested fields populated when available.
- Given a mixed accession list containing GCF_, GCA_, NC_, and NZ_ IDs, the system resolves each to an assembly and returns metadata; unresolved/invalid accessions are reported with actionable error messages.
- Rate limiting and retries prevent 429/5xx storms; logs show compliance with NCBI usage.
- JSON schema validates responses; CSV export matches schema projection.

## Risks and Mitigations
- NCBI API variability: Use both E-utilities and Datasets when advantageous; keep adapters modular.
- Throughput limits: Batch IDs, cache summaries, use job queue.
- Data gaps: Fill from multiple sources (Assembly, Nuccore, BioSample); mark provenance.
