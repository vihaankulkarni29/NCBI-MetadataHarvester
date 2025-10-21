"""Test different filter formats."""
import asyncio

from src.ncbi_metadata_harvester.ncbi_client import NCBIClient


async def test_filters():
    """Test different NCBI assembly filter formats."""
    async with NCBIClient() as client:
        test_queries = [
            ("No filter", "Escherichia coli K-12[Organism]"),
            ("refseq[filter]", "Escherichia coli K-12[Organism] AND refseq[filter]"),
            ("latest[filter]", "Escherichia coli K-12[Organism] AND latest[filter]"),
            ("refseq[Filter]", "Escherichia coli K-12[Organism] AND refseq[Filter]"),
            ("RefSeq category", "Escherichia coli K-12[Organism] AND refseq_category[Properties]"),
            ("All RefSeq", "Escherichia coli K-12[Organism] AND all[filter] NOT anomalous[filter]"),
        ]
        
        for name, term in test_queries:
            print(f"\n{name}")
            print(f"   Query: {term}")
            resp = await client.esearch(db="assembly", term=term, retmax=3)
            data = resp.json()
            count = data.get("esearchresult", {}).get("count", "0")
            id_list = data.get("esearchresult", {}).get("idlist", [])
            print(f"   Result: {count} total, {len(id_list)} returned")


if __name__ == "__main__":
    asyncio.run(test_filters())
