# Metadata Schema and Mapping

## Object Shape (JSON)
- accession: string (nuccore primary accession, e.g., NC_000913.3)
- version: string (e.g., NC_000913.3)
- locus: string
- definition: string
- dblink:
  - biosample: string | null
  - bioproject: string | null
- keywords: string[]
- source: string
- organism: string
- taxonomy: string[] (lineage)
- assembly:
  - accession: string (GCF_/GCA_)
  - name: string
  - level: string (Complete Genome/Chromosome/Scaffold/Contig)
  - refseq_category: string (reference/representative/na)
  - submitter: string | null
  - date: string | null
- references: Array<{
  - authors: string
  - title: string
  - journal: string
  - pubmed: string | null
  - remark: string | null
}>
- provenance: object (per-field source + timestamp)

## Mapping to NCBI Fields
- LOCUS -> GenBank LOCUS line (nuccore gb)
- DEFINITION -> GenBank DEFINITION line
- ACCESSION/VERSION -> GenBank ACCESSION/VERSION lines
- DBLINK -> GenBank DBLINK entries (BioSample, BioProject)
- KEYWORDS -> GenBank KEYWORDS list
- SOURCE -> GenBank SOURCE
- ORGANISM -> GenBank ORGANISM
- Taxonomy lineage -> GenBank ORGANISM block lines following organism name
- REFERENCES -> GenBank REFERENCE blocks with subfields AUTHORS, TITLE, JOURNAL, PUBMED, REMARK
- Assembly fields -> db=assembly esummary (DocumentSummary fields: AssemblyAccession, AssemblyName, AssemblyStatus/Level, RefSeq_category, Submitter, SubmissionDate)

## Multiple Sequences per Assembly
- Policy: Choose primary chromosome (linked via assembly_nuccore_refseq or assembly_nuccore link + filters for "chromosome"; prefer NC_ over NZ_/CP_)
- Optionally aggregate references across all chromosomes/plasmids; default to primary only for performance

## Example (abbreviated)
{
  "accession": "NC_000913.3",
  "version": "NC_000913.3",
  "locus": "U00096",
  "definition": "Escherichia coli str. K-12 substr. MG1655, complete genome",
  "dblink": {"biosample": "SAMN02604091", "bioproject": "PRJNA57779"},
  "keywords": ["RefSeq", "complete genome"],
  "source": "Escherichia coli str. K-12 substr. MG1655",
  "organism": "Escherichia coli",
  "taxonomy": ["Bacteria", "Proteobacteria", "Gammaproteobacteria", ...],
  "assembly": {"accession": "GCF_000005845.2", "name": "ASM584v2", "level": "Complete Genome", "refseq_category": "reference"},
  "references": [{"authors": "Blattner FR et al.", "title": "The complete genome...", "journal": "Science 277 (5331):1453-1462 (1997)", "pubmed": "9278503"}]
}
