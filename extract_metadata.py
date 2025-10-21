"""Extract metadata for first 50 genomes from accession list."""
import asyncio
import json
from pathlib import Path

import httpx


async def extract_metadata_from_file(accession_file: str, limit: int = 50, output_dir: str = "results"):
    """
    Extract metadata for accessions from a file.
    
    Args:
        accession_file: Path to file with one accession per line
        limit: Number of accessions to process (default 50)
        output_dir: Directory to save results
    """
    # Read accessions
    print(f"📖 Reading accessions from {accession_file}...")
    with open(accession_file, 'r') as f:
        accessions = [line.strip() for line in f if line.strip()]
    
    total_accessions = len(accessions)
    accessions_to_process = accessions[:limit]
    
    print(f"✅ Found {total_accessions} total accessions")
    print(f"🎯 Processing first {len(accessions_to_process)} accessions")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Submit job to API
    base_url = "http://127.0.0.1:8000"
    print(f"\n🚀 Submitting job to {base_url}...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Submit accession job
        payload = {"accessions": accessions_to_process}
        
        try:
            resp = await client.post(f"{base_url}/api/v1/jobs/accessions", json=payload)
            resp.raise_for_status()
            job_data = resp.json()
            job_id = job_data["job_id"]
            print(f"✅ Job created: {job_id}")
            print(f"   Status: {job_data['status']}")
        except httpx.ConnectError:
            print("\n❌ ERROR: Cannot connect to the API server!")
            print("   Please start the server first:")
            print("   python -m uvicorn src.ncbi_metadata_harvester.main:app --host 127.0.0.1 --port 8000")
            return
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return
        
        # Poll for completion
        print(f"\n⏳ Waiting for job to complete...")
        print("   (This may take several minutes for 50 genomes)")
        
        last_progress = {"completed": 0, "total": 0, "errors": 0}
        dots = 0
        status = "queued"
        
        for i in range(300):  # Max 10 minutes (300 * 2s)
            await asyncio.sleep(2)
            
            try:
                resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}")
                resp.raise_for_status()
                status_data = resp.json()
                
                status = status_data["status"]
                progress = status_data["progress"]
                
                # Show progress if changed
                if progress != last_progress:
                    elapsed = i * 2
                    print(f"\n   [{elapsed}s] Status: {status}")
                    print(f"         Progress: {progress['completed']}/{progress['total']}")
                    print(f"         Errors: {progress['errors']}")
                    last_progress = progress.copy()
                    dots = 0
                else:
                    # Show activity dots
                    if dots % 15 == 0:
                        print(".", end="", flush=True)
                    dots += 1
                
                if status in ["succeeded", "failed"]:
                    print(f"\n\n✅ Job {status}!")
                    break
            except Exception as e:
                print(f"\n❌ Error polling: {e}")
                return
        
        if status not in ["succeeded", "failed"]:
            print("\n⚠️  Job still running after timeout. Check status manually.")
            print(f"   Job ID: {job_id}")
            print(f"   Status URL: {base_url}/api/v1/jobs/{job_id}")
            return
        
        # Fetch results
        print(f"\n📥 Downloading results...")
        
        # Get JSON results
        resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}/results?format=json")
        resp.raise_for_status()
        results = resp.json()
        
        # Save JSON
        json_file = output_path / f"metadata_{job_id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved JSON: {json_file}")
        
        # Get CSV results
        resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}/results?format=csv")
        resp.raise_for_status()
        csv_content = resp.text
        
        # Save CSV
        csv_file = output_path / f"metadata_{job_id}.csv"
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        print(f"✅ Saved CSV: {csv_file}")
        
        # Show summary
        print(f"\n" + "="*70)
        print("📊 SUMMARY")
        print("="*70)
        print(f"Total accessions requested: {len(accessions_to_process)}")
        print(f"Successfully processed: {len(results['results'])}")
        print(f"Errors encountered: {len(results['errors'])}")
        
        if results['results']:
            print(f"\n✅ Sample results (first 3):")
            for i, r in enumerate(results['results'][:3], 1):
                print(f"\n  [{i}] {r.get('accession', 'N/A')} - {r.get('organism', 'Unknown')}")
                print(f"      Definition: {r.get('definition', 'N/A')[:70]}...")
                print(f"      BioSample: {r.get('dblink', {}).get('biosample', 'N/A')}")
                print(f"      BioProject: {r.get('dblink', {}).get('bioproject', 'N/A')}")
        
        if results['errors']:
            print(f"\n⚠️  Errors (first 5):")
            for err in results['errors'][:5]:
                print(f"      - {err}")
        
        print(f"\n" + "="*70)
        print(f"✨ Complete! Results saved to {output_path}/")
        print("="*70)


async def main():
    """Main entry point."""
    import sys
    
    # Parse command line args
    accession_file = "accession_list.txt"
    limit = 50
    
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"Usage: python {sys.argv[0]} [limit]")
            print(f"  limit: Number of accessions to process (default: 50)")
            return
    
    print("🔬 NCBI Metadata Harvester - Batch Extraction")
    print("="*70)
    
    await extract_metadata_from_file(accession_file, limit=limit)


if __name__ == "__main__":
    asyncio.run(main())
