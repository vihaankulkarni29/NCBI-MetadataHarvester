"""GenBank record parsing utilities."""
from io import StringIO
from typing import Any

try:
    from Bio import SeqIO
    BIOPYTHON_AVAILABLE = True
except ImportError:
    BIOPYTHON_AVAILABLE = False


def parse_genbank_record(genbank_text: str) -> dict[str, Any] | None:
    """
    Parse a GenBank format record and extract metadata fields.

    Args:
        genbank_text: GenBank format text

    Returns:
        Dictionary with extracted fields or None if parsing fails
    """
    if not BIOPYTHON_AVAILABLE:
        raise RuntimeError("Biopython is required for GenBank parsing but not installed")

    try:
        handle = StringIO(genbank_text)
        record = SeqIO.read(handle, "genbank")

        # Extract DBLINK
        dblink = {"biosample": None, "bioproject": None}
        if hasattr(record, "dbxrefs") and record.dbxrefs:
            for ref in record.dbxrefs:
                if ref.startswith("BioSample:"):
                    dblink["biosample"] = ref.replace("BioSample:", "")
                elif ref.startswith("BioProject:"):
                    dblink["bioproject"] = ref.replace("BioProject:", "")

        # Extract keywords
        keywords = []
        if hasattr(record, "annotations") and "keywords" in record.annotations:
            keywords = record.annotations.get("keywords", [])

        # Extract source and organism
        source = record.annotations.get("source", "")
        organism = record.annotations.get("organism", "")
        taxonomy = record.annotations.get("taxonomy", [])

        # Extract references
        references = []
        if hasattr(record, "annotations") and "references" in record.annotations:
            for ref in record.annotations["references"]:
                ref_data = {
                    "authors": getattr(ref, "authors", ""),
                    "title": getattr(ref, "title", ""),
                    "journal": getattr(ref, "journal", ""),
                    "pubmed": getattr(ref, "pubmed_id", None) or None,
                    "remark": getattr(ref, "comment", None) or None,
                }
                references.append(ref_data)

        return {
            "locus": record.name,
            "definition": record.description,
            "accession": record.id.split(".")[0] if "." in record.id else record.id,
            "version": record.id,
            "dblink": dblink,
            "keywords": keywords,
            "source": source,
            "organism": organism,
            "taxonomy": taxonomy,
            "references": references,
        }

    except Exception as e:
        # Log parse error but don't crash
        print(f"Failed to parse GenBank record: {e}")
        return None


def parse_genbank_batch(genbank_text: str) -> list[dict[str, Any]]:
    """
    Parse multiple GenBank records from a single text block.

    Args:
        genbank_text: GenBank format text with potentially multiple records

    Returns:
        List of parsed metadata dictionaries
    """
    if not BIOPYTHON_AVAILABLE:
        raise RuntimeError("Biopython is required for GenBank parsing but not installed")

    results = []
    try:
        handle = StringIO(genbank_text)
        for record in SeqIO.parse(handle, "genbank"):
            # Reuse single-record parser logic
            single_gb = record.format("genbank")
            parsed = parse_genbank_record(single_gb)
            if parsed:
                results.append(parsed)
    except Exception as e:
        print(f"Failed to parse GenBank batch: {e}")

    return results
