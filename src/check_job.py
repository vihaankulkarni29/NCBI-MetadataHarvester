"""Check job status and download results."""
import asyncio
import json
import sys

import httpx


async def check_job_status(job_id: str, base_url: str = "http://127.0.0.1:8000"):
    """Check the status of a running job and download results if ready."""
    
    print(f"🔍 Checking job status: {job_id}")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Get job status
            resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}")
            resp.raise_for_status()
            status_data = resp.json()
            
            print(f"\n📊 Job Status:")
            print(f"   Status: {status_data['status']}")
            print(f"   Submitted: {status_data['submitted_at']}")
            print(f"   Updated: {status_data['updated_at']}")
            
            progress = status_data['progress']
            print(f"\n📈 Progress:")
            print(f"   Total: {progress['total']}")
            print(f"   Completed: {progress['completed']}")
            print(f"   Errors: {progress['errors']}")
            
            if progress['total'] > 0:
                pct = (progress['completed'] / progress['total']) * 100
                print(f"   Percentage: {pct:.1f}%")
            
            # If succeeded, download results
            if status_data['status'] == 'succeeded':
                print(f"\n✅ Job completed successfully!")
                print(f"\n📥 Downloading results...")
                
                # Get results
                resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}/results?format=json")
                resp.raise_for_status()
                results = resp.json()
                
                print(f"\n📊 Results Summary:")
                print(f"   Genomes retrieved: {len(results['results'])}")
                print(f"   Errors: {len(results['errors'])}")
                
                # Save to file
                output_file = f"results/metadata_{job_id}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                print(f"\n✅ Saved to: {output_file}")
                
                # Show first few results
                if results['results']:
                    print(f"\n📋 First few results:")
                    for i, r in enumerate(results['results'][:3], 1):
                        print(f"\n   [{i}] {r.get('accession', 'N/A')}")
                        print(f"       Organism: {r.get('organism', 'Unknown')}")
                        print(f"       BioSample: {r.get('dblink', {}).get('biosample', 'N/A')}")
                
                # Show errors if any
                if results['errors']:
                    print(f"\n⚠️  Errors (first 5):")
                    for err in results['errors'][:5]:
                        print(f"      - {err}")
                
                # Download CSV too
                print(f"\n📥 Downloading CSV...")
                resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}/results?format=csv")
                resp.raise_for_status()
                csv_file = f"results/metadata_{job_id}.csv"
                with open(csv_file, 'w', encoding='utf-8') as f:
                    f.write(resp.text)
                print(f"✅ Saved to: {csv_file}")
                
            elif status_data['status'] == 'running':
                print(f"\n⏳ Job is still running...")
                print(f"   Processing {progress['completed']}/{progress['total']} genomes")
                print(f"\n💡 Tip: Run this script again in a few minutes to check progress")
                print(f"   python src/check_job.py {job_id}")
                
            elif status_data['status'] == 'failed':
                print(f"\n❌ Job failed!")
                # Try to get results to see errors
                try:
                    resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}/results?format=json")
                    results = resp.json()
                    if results.get('errors'):
                        print(f"\n⚠️  Errors:")
                        for err in results['errors']:
                            print(f"      - {err}")
                except:
                    print("   (Could not retrieve error details)")
            
            else:
                print(f"\n📋 Status: {status_data['status']}")
            
        except httpx.ConnectError:
            print(f"\n❌ ERROR: Cannot connect to {base_url}")
            print(f"   Make sure the server is running:")
            print(f"   python -m uvicorn src.ncbi_metadata_harvester.main:app --host 127.0.0.1 --port 8000")
        except httpx.HTTPStatusError as e:
            print(f"\n❌ HTTP Error: {e.response.status_code}")
            print(f"   {e.response.text}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    print("\n" + "=" * 70)


async def main():
    if len(sys.argv) < 2:
        print("Usage: python src/check_job.py <job_id>")
        print("\nExample:")
        print("  python src/check_job.py 3ebce10c-02d3-448b-a224-4290ec9583cd")
        sys.exit(1)
    
    job_id = sys.argv[1]
    await check_job_status(job_id)


if __name__ == "__main__":
    asyncio.run(main())
