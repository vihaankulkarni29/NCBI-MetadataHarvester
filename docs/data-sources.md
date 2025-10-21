# Data Sources and Access Methods

## Options
1) NCBI E-utilities (Entrez): esearch, esummary, elink, efetch
- Pros: Very flexible; access to Assembly/Nuccore/BioSample/BioProject; GenBank flatfiles via efetch (needed for LOCUS/REFERENCE)
- Cons: Careful with rate limits; responses are XML/JSON; more plumbing needed

2) NCBI Datasets API
- Pros: Modern JSON; convenient for assembly/genome metadata; can fetch GBFF bundles
- Cons: May not expose classic GenBank reference fields as richly as flatfiles

3) Biopython parsing of GenBank flatfiles (from efetch or Datasets)
- Pros: Direct access to GenBank lines (LOCUS, DEFINITION, KEYWORDS, DBLINK, REFERENCE, etc.)
- Cons: Requires downloading GBFF content per record (heavier than summaries)

## Recommended Hybrid Strategy
- Discovery and filtering: E-utilities esearch in db=assembly (prefer RefSeq, latest, assembly_level)
- Normalized assembly metadata: esummary(db=assembly) + Datasets (optional) for robustness
- GenBank fields: efetch(db=nuccore, rettype=gbwithparts or gb) for representative sequence(s)
- Cross-linking: elink(assembly->nuccore), elink(nuccore->biosample/bioproject when needed)

## Rate Limits and Politeness
- Without API key: up to ~3 requests/second; with API key: up to ~10 requests/second
- Always set tool/email (e.g., &tool=ncbi-metadata-harvester&email=user@example.com)
- Use batching where supported (ID lists in esummary/efetch)
- Exponential backoff on 429/5xx; jitter; max retries with circuit-breaker

## Authentication
- E-utilities supports API key (parameter api_key); store in secret env var
- Datasets generally does not require auth for public data

## Provenance
- Record which endpoints populated each field (e.g., source: "nuccore.efetch") and timestamps
