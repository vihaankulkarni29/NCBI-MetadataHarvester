"""Test NCBI search directly."""
import asyncio

from src.ncbi_metadata_harvester.ncbi_client import NCBIClient


async def test_ncbi_search():
    """Test direct NCBI assembly search."""
    async with NCBIClient() as client:
        # Test simple E. coli query
        term1 = "Escherichia coli K-12[Organism] AND refseq[filter] AND latest[filter]"
        print(f"\n1️⃣  Testing: {term1}")
        resp = await client.esearch(db="assembly", term=term1, retmax=5)
        data = resp.json()
        id_list = data.get("esearchresult", {}).get("idlist", [])
        count = data.get("esearchresult", {}).get("count", "0")
        print(f"   Found {count} assemblies, returned {len(id_list)} IDs")
        if id_list:
            print(f"   IDs: {id_list[:3]}")
        
        # Test even simpler query
        term2 = "Escherichia coli[Organism] AND refseq[filter]"
        print(f"\n2️⃣  Testing: {term2}")
        resp = await client.esearch(db="assembly", term=term2, retmax=5)
        data = resp.json()
        id_list = data.get("esearchresult", {}).get("idlist", [])
        count = data.get("esearchresult", {}).get("count", "0")
        print(f"   Found {count} assemblies, returned {len(id_list)} IDs")
        if id_list:
            print(f"   IDs: {id_list[:3]}")
        
        # Test minimal query
        term3 = "Escherichia coli[Organism]"
        print(f"\n3️⃣  Testing: {term3}")
        resp = await client.esearch(db="assembly", term=term3, retmax=5)
        data = resp.json()
        id_list = data.get("esearchresult", {}).get("idlist", [])
        count = data.get("esearchresult", {}).get("count", "0")
        print(f"   Found {count} assemblies, returned {len(id_list)} IDs")
        if id_list:
            print(f"   IDs: {id_list[:3]}")
            
            # Try to get summary for first assembly
            print(f"\n4️⃣  Getting summary for {id_list[0]}...")
            sum_resp = await client.esummary(db="assembly", id=[id_list[0]])
            sum_data = sum_resp.json()
            result = sum_data.get("result", {})
            doc = result.get(id_list[0], {})
            print(f"   Accession: {doc.get('assemblyaccession', 'N/A')}")
            print(f"   Name: {doc.get('assemblyname', 'N/A')}")
            print(f"   Organism: {doc.get('organism', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(test_ncbi_search())
