# Search and Accession Resolution Logic

## Free-text Query Flow
1) Parse input: organism, keywords, filters (assembly_level, latest_only, source_db_preference), limit
2) Build ESearch term for db=assembly:
   - organism -> "Escherichia coli[Organism]"
   - keywords -> combined OR terms in All Fields or Title/Keywords
   - filters -> "latest[filter]" if latest_only; add assembly_level filter (e.g., "(complete genome[Assembly Level])")
   - source pref -> prefer RefSeq by filtering to "refseq[filter]" or post-filter results to GCF_
3) esearch(db=assembly, retmax=limit*2 for headroom) -> assembly UIDs
4) esummary(db=assembly, id=UIDs) -> details; filter/sort: prefer RefSeq, latest version, desired assembly level
5) For each assembly:
   - Get AssemblyAccession (GCF_/GCA_), RefSeq_category, status/level
   - elink(dbfrom=assembly, db=nuccore, linkname=assembly_nuccore_refseq) -> linked nuccore IDs
   - pick primary chromosome (prefer accession starting with NC_ and molecule type "chromosome")
   - efetch(db=nuccore, id=chosen IDs, rettype=gb, retmode=text) -> parse GenBank for fields
   - enrich BioSample/BioProject if missing via DBLINK or elink to biosample/bioproject
6) Stop when limit genomes collected

## Accession List Flow
For each accession in input:
- Detect type via regex:
  - Assembly: ^GCF_|^GCA_
  - RefSeq genomic: ^NC_|^NR_|^NG_|^NZ_|^NT_|^NW_ (we care about genomic NC_/NZ_)
  - WGS/contig: ^CP|^CM|^CH|^AE|^AJ (non-exhaustive; treat as nuccore)
- If assembly:
  - Resolve to nuccore via elink(assembly->nuccore); pick primary chromosome; efetch gb
- If nuccore:
  - Optionally resolve to owning assembly via elink(nuccore->assembly) to populate assembly fields
  - efetch gb for GenBank fields
- If BioSample/BioProject given: attempt to resolve to assembly via elink/esearch
- De-duplicate by assembly accession; prefer RefSeq representations

## Deduplication & Preferences
- Prefer GCF_ over GCA_ when both exist for same assembly
- Prefer latest version (e.g., GCF_... .2 over .1)
- Prefer NC_ over NZ_/CP_ when multiple sequences qualify

## Errors and Edge Cases
- Missing DBLINK: try BioSample from esummary or linked BioSample
- No primary chromosome (scaffold assemblies): choose the largest scaffolds; mark as non-complete
- Accessions not found: include in errors with reason
- Network/timeouts: retry with backoff; cap total job time
