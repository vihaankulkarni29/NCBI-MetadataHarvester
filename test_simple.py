"""Simple integration test with a guaranteed query."""
import asyncio
import time

import httpx


async def test_simple_query():
    """Test with a simple query that should return results."""
    base_url = "http://127.0.0.1:8000"
    
    print("🔬 Simple Integration Test - E. coli K-12")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Simple query for E. coli strain K-12 (very well known strain)
        payload = {
            "organism": "Escherichia coli K-12",
            "filters": {
                "source_db_preference": "RefSeq",
                "latest_only": True
            },
            "limit": 1
        }
        
        print(f"\n1️⃣  Submitting query: {payload['organism']}")
        resp = await client.post(f"{base_url}/api/v1/jobs/query", json=payload)
        resp.raise_for_status()
        job_data = resp.json()
        job_id = job_data["job_id"]
        print(f"✅ Job: {job_id}")
        
        # Poll
        print("\n2️⃣  Polling...")
        for i in range(30):  # Max 60 seconds
            await asyncio.sleep(2)
            resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}")
            resp.raise_for_status()
            status_data = resp.json()
            
            status = status_data["status"]
            prog = status_data["progress"]
            print(f"   [{i*2}s] {status} | {prog['completed']}/{prog['total']} | Errors: {prog['errors']}")
            
            if status in ["succeeded", "failed"]:
                break
        
        if status != "succeeded":
            print(f"\n❌ Failed: {status}")
            # Show error
            resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}/results?format=json")
            data = resp.json()
            print(f"Errors: {data.get('errors', [])}")
            return
        
        # Get results
        print("\n3️⃣  Results:")
        resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}/results?format=json")
        resp.raise_for_status()
        results = resp.json()
        
        print(f"   Found: {len(results['results'])} genome(s)")
        print(f"   Errors: {len(results['errors'])}")
        
        if results['results']:
            r = results['results'][0]
            print(f"\n   ✅ Genome 1:")
            print(f"      Accession: {r.get('accession', 'N/A')}")
            print(f"      Version: {r.get('version', 'N/A')}")
            print(f"      Organism: {r.get('organism', 'N/A')}")
            print(f"      Definition: {r.get('definition', 'N/A')[:80]}...")
            print(f"      BioSample: {r.get('dblink', {}).get('biosample', 'N/A')}")
            print(f"      BioProject: {r.get('dblink', {}).get('bioproject', 'N/A')}")
            
            # Check assembly
            if 'assembly' in r:
                asm = r['assembly']
                print(f"      Assembly: {asm.get('accession', 'N/A')}")
                print(f"      Level: {asm.get('level', 'N/A')}")
                print(f"      Name: {asm.get('name', 'N/A')}")
            
            # Check references
            refs = r.get('references', [])
            if refs:
                print(f"      References: {len(refs)}")
                ref1 = refs[0]
                print(f"         [1] {ref1.get('title', 'N/A')[:60]}...")
                print(f"             PubMed: {ref1.get('pubmed', 'N/A')}")
        else:
            print("\n   ⚠️  No results (check errors)")
            for err in results.get('errors', []):
                print(f"      - {err}")
        
        print("\n" + "=" * 60)
        print("✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(test_simple_query())
