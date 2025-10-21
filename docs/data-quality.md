# Data Quality and Validation Plan

## Selection Rules
- Prefer RefSeq (GCF_) assemblies over GenBank (GCA_) when both map to same genome
- Prefer latest assembly version and latest sequence versions (e.g., NC_... .3)
- Prefer primary chromosome record for metadata; optionally add plasmids

## Validation Checks
- Required fields present: accession, definition, organism, assembly accession
- DBLINK contains BioSample or BioProject when available; otherwise attempt recovery via elink/esummary
- References parsed and at least one present when available in GB
- Consistency between assembly taxon and nuccore organism

## Gap Filling
- If KEYWORDS missing: derive from assembly category/status; add inferred tags (e.g., "complete genome")
- If DBLINK missing: try linked BioSample from assembly summary
- If ORGANISM lineage missing: fetch Taxonomy via esummary(db=taxonomy)

## Tests
- Unit tests for parsers on known GBFF examples (E. coli MG1655)
- Integration tests hitting NCBI in CI with very small sample and high throttling
- Golden JSON snapshots for a handful of accessions
