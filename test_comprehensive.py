"""Comprehensive integration test."""
import asyncio
import time

import httpx


async def test_comprehensive():
    """Test with multiple scenarios."""
    base_url = "http://127.0.0.1:8000"
    
    print("🔬 NCBI Metadata Harvester - Comprehensive Test")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Test 1: Query with keywords
        print("\n" + "=" * 70)
        print("TEST 1: Query-based search with keywords")
        print("=" * 70)
        
        payload = {
            "organism": "Salmonella enterica",
            "keywords": ["serovar Typhimurium"],
            "filters": {
                "assembly_level": ["Complete Genome"],
                "source_db_preference": "RefSeq",
                "latest_only": True
            },
            "limit": 2
        }
        
        print(f"Query: {payload['organism']} + {payload['keywords']}")
        resp = await client.post(f"{base_url}/api/v1/jobs/query", json=payload)
        resp.raise_for_status()
        job1_id = resp.json()["job_id"]
        print(f"✅ Job {job1_id} created")
        
        # Test 2: Accession list
        print("\n" + "=" * 70)
        print("TEST 2: Accession list resolution")
        print("=" * 70)
        
        payload = {
            "accessions": ["GCF_000005845.2", "NC_003197.2"]  # E. coli O157 and Salmonella
        }
        
        print(f"Accessions: {payload['accessions']}")
        resp = await client.post(f"{base_url}/api/v1/jobs/accessions", json=payload)
        resp.raise_for_status()
        job2_id = resp.json()["job_id"]
        print(f"✅ Job {job2_id} created")
        
        # Poll both jobs
        jobs = {
            job1_id: "Query-based",
            job2_id: "Accession-based"
        }
        
        print("\n" + "=" * 70)
        print("POLLING STATUS")
        print("=" * 70)
        
        completed = {}
        for _ in range(60):  # Max 120 seconds
            for job_id, job_type in jobs.items():
                if job_id in completed:
                    continue
                
                resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}")
                resp.raise_for_status()
                status_data = resp.json()
                
                status = status_data["status"]
                prog = status_data["progress"]
                
                if status in ["succeeded", "failed"]:
                    completed[job_id] = status
                    print(f"✅ {job_type} ({job_id[:8]}...): {status.upper()}")
                    print(f"   Progress: {prog['completed']}/{prog['total']}, Errors: {prog['errors']}")
            
            if len(completed) == len(jobs):
                break
            
            await asyncio.sleep(2)
        
        # Display results
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        
        for job_id, job_type in jobs.items():
            print(f"\n{job_type} Job ({job_id[:8]}...):")
            print("-" * 70)
            
            resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}/results?format=json")
            resp.raise_for_status()
            results = resp.json()
            
            print(f"✅ Retrieved {len(results['results'])} genome(s)")
            print(f"⚠️  Errors: {len(results['errors'])}")
            
            for i, r in enumerate(results["results"], 1):
                print(f"\n  [{i}] {r.get('organism', 'Unknown')}")
                print(f"      Accession: {r.get('accession', 'N/A')}")
                print(f"      Version: {r.get('version', 'N/A')}")
                print(f"      Definition: {r.get('definition', 'N/A')[:70]}...")
                print(f"      BioSample: {r.get('dblink', {}).get('biosample', 'N/A')}")
                print(f"      BioProject: {r.get('dblink', {}).get('bioproject', 'N/A')}")
                
                if 'assembly' in r:
                    asm = r['assembly']
                    print(f"      Assembly: {asm.get('accession', 'N/A')} ({asm.get('level', 'N/A')})")
                
                refs = r.get('references', [])
                if refs:
                    print(f"      References: {len(refs)} publication(s)")
                    if refs[0].get('pubmed'):
                        print(f"         [1] PMID:{refs[0]['pubmed']} - {refs[0].get('title', '')[:50]}...")
            
            if results['errors']:
                print(f"\n  ⚠️  Errors:")
                for err in results['errors'][:3]:
                    print(f"      - {err}")
        
        # Test CSV export
        print("\n" + "=" * 70)
        print("CSV EXPORT TEST")
        print("=" * 70)
        
        resp = await client.get(f"{base_url}/api/v1/jobs/{job1_id}/results?format=csv")
        resp.raise_for_status()
        csv_content = resp.text
        lines = csv_content.strip().split("\n")
        print(f"✅ CSV exported: {len(lines)} lines")
        print(f"   Header columns: {len(lines[0].split(','))} fields")
        print(f"   First few columns: {','.join(lines[0].split(',')[:5])}...")
        
        print("\n" + "=" * 70)
        print("🎉 ALL TESTS COMPLETE!")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_comprehensive())
