"""CSV export utilities."""
import io
from typing import Any

import pandas as pd


def export_results_to_csv(results: list[dict[str, Any]]) -> str:
    """
    Export metadata results to CSV format.

    Args:
        results: List of metadata dictionaries

    Returns:
        CSV string
    """
    if not results:
        return "No results to export"

    # Flatten nested structures for CSV
    flattened = []
    for result in results:
        flat = {
            "accession": result.get("accession", ""),
            "version": result.get("version", ""),
            "locus": result.get("locus", ""),
            "definition": result.get("definition", ""),
            "organism": result.get("organism", ""),
            "source": result.get("source", ""),
            "biosample": result.get("dblink", {}).get("biosample", ""),
            "bioproject": result.get("dblink", {}).get("bioproject", ""),
            "keywords": "; ".join(result.get("keywords", [])),
            "taxonomy": "; ".join(result.get("taxonomy", [])),
            "assembly_accession": result.get("assembly", {}).get("accession", ""),
            "assembly_name": result.get("assembly", {}).get("name", ""),
            "assembly_level": result.get("assembly", {}).get("level", ""),
            "refseq_category": result.get("assembly", {}).get("refseq_category", ""),
        }
        
        # Add first reference if available
        refs = result.get("references", [])
        if refs:
            ref = refs[0]
            flat["ref_authors"] = ref.get("authors", "")
            flat["ref_title"] = ref.get("title", "")
            flat["ref_journal"] = ref.get("journal", "")
            flat["ref_pubmed"] = ref.get("pubmed", "")
        else:
            flat["ref_authors"] = ""
            flat["ref_title"] = ""
            flat["ref_journal"] = ""
            flat["ref_pubmed"] = ""
        
        flattened.append(flat)
    
    # Create DataFrame and export to CSV
    df = pd.DataFrame(flattened)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()
