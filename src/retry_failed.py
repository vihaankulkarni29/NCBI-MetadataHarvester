"""Retry failed accessions from a previous job."""
import asyncio
import json
import sys
from pathlib import Path

import httpx


async def retry_failed_accessions(original_job_id: str, base_url: str = "http://127.0.0.1:8000"):
    """
    Extract failed accessions from a job and retry them.
    
    Args:
        original_job_id: Job ID that had errors
        base_url: API base URL
    """
    print(f"🔄 Retrying failed accessions from job: {original_job_id}")
    print("=" * 70)
    
    # Load the original results
    results_file = f"results/metadata_{original_job_id}.json"
    if not Path(results_file).exists():
        print(f"❌ Results file not found: {results_file}")
        print(f"   Make sure the job completed and results were saved.")
        return
    
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Extract failed accessions from errors
    errors = results.get('errors', [])
    if not errors:
        print("✅ No errors found in the original job!")
        print("   All accessions were processed successfully.")
        return
    
    print(f"\n⚠️  Found {len(errors)} error(s):")
    for err in errors[:10]:
        print(f"   - {err}")
    if len(errors) > 10:
        print(f"   ... and {len(errors) - 10} more")
    
    # Extract accession IDs from error messages
    # Error format: "Error processing CP184062.1: ..." or "Assembly not found: GCF_..."
    failed_accessions = []
    for err in errors:
        # Try different patterns
        if "Error processing" in err:
            # Extract "CP184062.1" from "Error processing CP184062.1: ..."
            parts = err.split("Error processing ")
            if len(parts) > 1:
                acc = parts[1].split(":")[0].strip()
                failed_accessions.append(acc)
        elif "not found:" in err or "Assembly not found:" in err:
            # Extract "GCF_..." from "Assembly not found: GCF_..."
            parts = err.split(":")
            if len(parts) > 1:
                acc = parts[-1].strip()
                failed_accessions.append(acc)
        elif "No nuccore link for" in err:
            # Extract from "No nuccore link for GCF_..."
            parts = err.split("for ")
            if len(parts) > 1:
                acc = parts[1].strip()
                failed_accessions.append(acc)
    
    if not failed_accessions:
        print(f"\n⚠️  Could not automatically extract accession IDs from errors.")
        print(f"   Please manually check the errors and submit them via the API or clients/metadata_client.py")
        return
    
    print(f"\n📋 Extracted {len(failed_accessions)} failed accession(s):")
    for acc in failed_accessions:
        print(f"   - {acc}")
    
    # Submit retry job
    print(f"\n🚀 Submitting retry job...")
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            payload = {"accessions": failed_accessions}
            resp = await client.post(f"{base_url}/api/v1/jobs/accessions", json=payload)
            resp.raise_for_status()
            job_data = resp.json()
            retry_job_id = job_data["job_id"]
            
            print(f"✅ Retry job created: {retry_job_id}")
            print(f"   Status: {job_data['status']}")
            
            # Monitor the retry job
            print(f"\n⏳ Monitoring retry job...")
            status = "queued"
            for i in range(300):  # 10 minutes max for retries
                await asyncio.sleep(2)
                
                resp = await client.get(f"{base_url}/api/v1/jobs/{retry_job_id}")
                resp.raise_for_status()
                status_data = resp.json()
                
                status = status_data["status"]
                progress = status_data["progress"]
                
                if i % 5 == 0:  # Print every 10 seconds
                    print(f"   [{i*2}s] {status} | {progress['completed']}/{progress['total']} | Errors: {progress['errors']}")
                
                if status in ["succeeded", "failed"]:
                    break
            
            if status != "succeeded":
                print(f"\n⚠️  Retry job status: {status}")
                print(f"   Check manually: python src/check_job.py {retry_job_id}")
                return
            
            # Get retry results
            print(f"\n✅ Retry job completed!")
            resp = await client.get(f"{base_url}/api/v1/jobs/{retry_job_id}/results?format=json")
            resp.raise_for_status()
            retry_results = resp.json()
            
            print(f"\n📊 Retry Results:")
            print(f"   Successfully retrieved: {len(retry_results['results'])}")
            print(f"   Still failed: {len(retry_results['errors'])}")
            
            # Merge with original results
            print(f"\n🔗 Merging with original results...")
            merged_results = {
                "results": results['results'] + retry_results['results'],
                "errors": retry_results['errors']  # Keep only new errors
            }
            
            # Save merged results
            merged_file = f"results/metadata_{original_job_id}_merged.json"
            with open(merged_file, 'w', encoding='utf-8') as f:
                json.dump(merged_results, f, indent=2, ensure_ascii=False)
            print(f"✅ Merged results saved: {merged_file}")
            
            # Also save CSV
            print(f"\n📥 Generating merged CSV...")
            # For CSV, we need to re-submit merged accessions or manually create
            # Simpler: just save the retry CSV separately
            resp = await client.get(f"{base_url}/api/v1/jobs/{retry_job_id}/results?format=csv")
            resp.raise_for_status()
            retry_csv_file = f"results/metadata_{original_job_id}_retry.csv"
            with open(retry_csv_file, 'w', encoding='utf-8') as f:
                f.write(resp.text)
            print(f"✅ Retry CSV saved: {retry_csv_file}")
            
            print(f"\n" + "=" * 70)
            print(f"📊 FINAL SUMMARY:")
            print(f"   Original: {len(results['results'])} genomes")
            print(f"   Retry: {len(retry_results['results'])} genomes")
            print(f"   Total: {len(merged_results['results'])} genomes")
            print(f"   Remaining errors: {len(merged_results['errors'])}")
            
            if merged_results['errors']:
                print(f"\n⚠️  Still have {len(merged_results['errors'])} error(s):")
                for err in merged_results['errors'][:5]:
                    print(f"      - {err}")
            else:
                print(f"\n🎉 All accessions successfully retrieved!")
            
            print(f"\n📁 Files:")
            print(f"   Original: {results_file}")
            print(f"   Merged: {merged_file}")
            print(f"   Retry CSV: {retry_csv_file}")
            
        except httpx.ConnectError:
            print(f"\n❌ Cannot connect to {base_url}")
            print(f"   Make sure the server is running!")
        except Exception as e:
            print(f"\n❌ Error: {e}")


async def main():
    if len(sys.argv) < 2:
        print("Usage: python src/retry_failed.py <original_job_id>")
        print("\nExample:")
        print("  python src/retry_failed.py 3ebce10c-02d3-448b-a224-4290ec9583cd")
        print("\nThis will:")
        print("  1. Read errors from the original job results")
        print("  2. Extract failed accession IDs")
        print("  3. Submit a new job to retry them")
        print("  4. Merge successful results with the original")
        sys.exit(1)
    
    original_job_id = sys.argv[1]
    await retry_failed_accessions(original_job_id)


if __name__ == "__main__":
    asyncio.run(main())
