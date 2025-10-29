"""Monitor a job until completion with live progress updates."""
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx


async def monitor_job(job_id: str, base_url: str = "http://127.0.0.1:8000", check_interval: int = 10):
    """Monitor a job until completion with live updates."""
    
    print(f"🔍 Monitoring job: {job_id}")
    print("=" * 70)
    print(f"⏱️  Checking every {check_interval} seconds (Ctrl+C to stop)\n")
    
    last_completed = -1
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            while True:
                try:
                    # Get job status
                    resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}")
                    resp.raise_for_status()
                    status_data = resp.json()
                    
                    status = status_data['status']
                    progress = status_data['progress']
                    elapsed = time.time() - start_time
                    
                    # Show progress if changed
                    if progress['completed'] != last_completed:
                        elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
                        pct = (progress['completed'] / progress['total'] * 100) if progress['total'] > 0 else 0
                        
                        print(f"[{elapsed_str}] Status: {status} | "
                              f"Progress: {progress['completed']}/{progress['total']} ({pct:.1f}%) | "
                              f"Errors: {progress['errors']}")
                        
                        # Estimate time remaining
                        if progress['completed'] > 0 and elapsed > 0:
                            rate = progress['completed'] / elapsed
                            remaining = (progress['total'] - progress['completed']) / rate
                            remaining_str = time.strftime("%H:%M:%S", time.gmtime(remaining))
                            print(f"         Est. time remaining: {remaining_str}")
                        
                        last_completed = progress['completed']
                    
                    # Check if job is complete
                    if status == 'succeeded':
                        print(f"\n✅ Job completed successfully!")
                        elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
                        print(f"   Total time: {elapsed_str}")
                        
                        # Download results
                        print(f"\n📥 Downloading results...")
                        resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}/results?format=json")
                        resp.raise_for_status()
                        results = resp.json()
                        
                        # Save JSON
                        Path("results").mkdir(exist_ok=True)
                        json_file = f"results/metadata_{job_id}.json"
                        with open(json_file, 'w', encoding='utf-8') as f:
                            json.dump(results, f, indent=2, ensure_ascii=False)
                        print(f"✅ JSON saved: {json_file}")
                        
                        # Save CSV
                        resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}/results?format=csv")
                        resp.raise_for_status()
                        csv_file = f"results/metadata_{job_id}.csv"
                        with open(csv_file, 'w', encoding='utf-8') as f:
                            f.write(resp.text)
                        print(f"✅ CSV saved: {csv_file}")
                        
                        print(f"\n📊 Summary:")
                        print(f"   Genomes retrieved: {len(results['results'])}")
                        print(f"   Errors: {len(results['errors'])}")
                        
                        if results['results']:
                            print(f"\n📋 Sample results (first 3):")
                            for i, r in enumerate(results['results'][:3], 1):
                                print(f"   [{i}] {r.get('accession', 'N/A')} - {r.get('organism', 'Unknown')}")
                        
                        if results['errors']:
                            print(f"\n⚠️  Errors (first 5):")
                            for err in results['errors'][:5]:
                                print(f"      - {err}")
                        
                        break
                    
                    elif status == 'failed':
                        print(f"\n❌ Job failed!")
                        try:
                            resp = await client.get(f"{base_url}/api/v1/jobs/{job_id}/results?format=json")
                            results = resp.json()
                            if results.get('errors'):
                                print(f"\n⚠️  Errors:")
                                for err in results['errors']:
                                    print(f"      - {err}")
                        except:
                            pass
                        break
                    
                    # Wait before next check
                    await asyncio.sleep(check_interval)
                
                except httpx.HTTPStatusError as e:
                    print(f"\n❌ HTTP Error: {e.response.status_code}")
                    break
                except httpx.ConnectError:
                    print(f"\n❌ Cannot connect to server. Is it running?")
                    break
        
        except KeyboardInterrupt:
            print(f"\n\n⚠️  Monitoring stopped by user")
            print(f"   Job is still running. Check again with:")
            print(f"   python src/check_job.py {job_id}")
    
    print("\n" + "=" * 70)


async def main():
    if len(sys.argv) < 2:
        print("Usage: python src/monitor_job.py <job_id> [check_interval_seconds]")
        print("\nExample:")
        print("  python src/monitor_job.py 3ebce10c-02d3-448b-a224-4290ec9583cd")
        print("  python src/monitor_job.py 3ebce10c-02d3-448b-a224-4290ec9583cd 5")
        sys.exit(1)
    
    job_id = sys.argv[1]
    check_interval = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    await monitor_job(job_id, check_interval=check_interval)


if __name__ == "__main__":
    asyncio.run(main())
