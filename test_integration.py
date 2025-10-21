"""Manual integration test - submit a real query and check results."""
import asyncio
import time

import httpx


async def test_end_to_end():
    """Test the full pipeline with a small real query."""
    base_url = "http://127.0.0.1:8000"
    
    print("🔬 NCBI Metadata Harvester - Integration Test")
    print("=" * 60)
    
    # Submit a query job
    print("\n1️⃣  Submitting query job for E. coli (limit 2)...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {
            "organism": "Escherichia coli",
            "keywords": ["K-12"],
            "filters": {
                "assembly_level": ["Complete Genome"],
                "source_db_preference": "RefSeq",
                "latest_only": True
            },
            "limit": 2
        }
        
        resp = await client.post(f"{base_url}/api/v1/jobs/query", json=payload)
        resp.raise_for_status()
        job_data = resp.json()
        job_id = job_data["job_id"]
        print(f"✅ Job created: {job_id}")
        print(f"   Status: {job_data['status']}")
        
        # Poll for completion
        print("\n2️⃣  Polling for job completion...")
        max_wait = 60  # seconds
        start = time.time()
        status = "queued"
        
        while time.time() - start < max_wait:
            resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}")
            resp.raise_for_status()
            status_data = resp.json()
            
            status = status_data["status"]
            progress = status_data["progress"]
            print(f"   Status: {status} | Progress: {progress['completed']}/{progress['total']} | Errors: {progress['errors']}")
            
            if status in ["succeeded", "failed"]:
                break
            
            await asyncio.sleep(2)
        
        if status != "succeeded":
            print(f"❌ Job did not succeed: {status}")
            return
        
        print("\n✅ Job succeeded!")
        
        # Get results
        print("\n3️⃣  Fetching results (JSON)...")
        resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}/results?format=json")
        resp.raise_for_status()
        results = resp.json()
        
        print(f"\n📊 Retrieved {len(results['results'])} genome(s)")
        print(f"   Errors: {len(results['errors'])}")
        
        for i, result in enumerate(results["results"], 1):
            print(f"\n   Genome {i}:")
            print(f"      Accession: {result.get('accession', 'N/A')}")
            print(f"      Version: {result.get('version', 'N/A')}")
            print(f"      Organism: {result.get('organism', 'N/A')}")
            print(f"      Definition: {result.get('definition', 'N/A')[:80]}...")
            print(f"      BioSample: {result.get('dblink', {}).get('biosample', 'N/A')}")
            print(f"      BioProject: {result.get('dblink', {}).get('bioproject', 'N/A')}")
            print(f"      Assembly: {result.get('assembly', {}).get('accession', 'N/A')}")
            print(f"      Assembly Level: {result.get('assembly', {}).get('level', 'N/A')}")
            
            refs = result.get('references', [])
            if refs:
                print(f"      References: {len(refs)}")
                ref = refs[0]
                print(f"         Title: {ref.get('title', 'N/A')[:60]}...")
                print(f"         PubMed: {ref.get('pubmed', 'N/A')}")
        
        if results['errors']:
            print(f"\n⚠️  Errors encountered:")
            for err in results['errors'][:3]:
                print(f"      - {err}")
        
        # Test CSV export
        print("\n4️⃣  Testing CSV export...")
        resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}/results?format=csv")
        resp.raise_for_status()
        csv_content = resp.text
        lines = csv_content.strip().split("\n")
        print(f"✅ CSV exported: {len(lines)} lines (including header)")
        print(f"   Header: {lines[0][:100]}...")
        
        print("\n" + "=" * 60)
        print("🎉 Integration test complete!")


if __name__ == "__main__":
    print("⚠️  Make sure the server is running:")
    print("   python -m uvicorn src.ncbi_metadata_harvester.main:app --reload\n")
    asyncio.run(test_end_to_end())
