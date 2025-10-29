# Quick Start Guide: Extracting Metadata from Your Accession List

## Prerequisites

1. **Start the API server** (in a separate terminal):
   ```powershell
   python -m uvicorn src.ncbi_metadata_harvester.main:app --host 127.0.0.1 --port 8000
   ```

2. **Make sure you have your `.env` file** with your NCBI API key:
   ```
   NCBI_API_KEY=your_api_key_here
   NCBI_EMAIL=your_email@example.com
   NCBI_TOOL=ncbi-metadata-harvester
   ```

## Method 1: Using the Extraction Script (Recommended)

### Extract first 50 genomes:
```powershell
python src/extract_metadata.py
```

### Extract a different number (e.g., 100):
```powershell
python src/extract_metadata.py 100
```

### What it does:
- Reads accessions from `accession_list.txt`
- Submits them to the API
- Polls until complete (shows progress)
- Saves results to `results/` folder:
  - `metadata_{job_id}.json` - Full JSON with all fields
  - `metadata_{job_id}.csv` - CSV export (flattened)

### Expected output:
```
🔬 NCBI Metadata Harvester - Batch Extraction
======================================================================
📖 Reading accessions from accession_list.txt...
✅ Found 61161 total accessions
🎯 Processing first 50 accessions

🚀 Submitting job to http://127.0.0.1:8000...
✅ Job created: abc123...
   Status: queued

⏳ Waiting for job to complete...
   (This may take several minutes for 50 genomes)
   [10s] Status: running
         Progress: 5/50
         Errors: 0
...
✅ Job succeeded!
📥 Downloading results...
✅ Saved JSON: results/metadata_abc123.json
✅ Saved CSV: results/metadata_abc123.csv
```

## Method 2: Using PowerShell and Invoke-RestMethod

### 1. Start the server (separate terminal):
```powershell
python -m uvicorn src.ncbi_metadata_harvester.main:app --host 127.0.0.1 --port 8000
```

### 2. Prepare your accessions:
```powershell
# Read first 50 accessions
$accessions = Get-Content accession_list.txt | Select-Object -First 50
```

### 3. Submit the job:
```powershell
$body = @{
    accessions = $accessions
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/jobs/accessions" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"

$jobId = $response.job_id
Write-Host "Job ID: $jobId"
```

### 4. Check status:
```powershell
$status = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/jobs/$jobId"
$status | ConvertTo-Json
```

### 5. Get results (once status = "succeeded"):
```powershell
# Get JSON
$results = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/jobs/$jobId/results?format=json"
$results | ConvertTo-Json -Depth 10 | Out-File "results.json"

# Get CSV
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/jobs/$jobId/results?format=csv" `
    | Out-File "results.csv"
```

## Method 3: Using Python Directly

```python
import asyncio
import httpx

async def extract_50_genomes():
    # Read accessions
    with open("accession_list.txt") as f:
        accessions = [line.strip() for line in f if line.strip()][:50]
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Submit job
        resp = await client.post(
            "http://127.0.0.1:8000/api/v1/jobs/accessions",
            json={"accessions": accessions}
        )
        job_id = resp.json()["job_id"]
        print(f"Job ID: {job_id}")
        
        # Poll until complete
        while True:
            resp = await client.get(f"http://127.0.0.1:8000/api/v1/jobs/{job_id}")
            status_data = resp.json()
            print(f"Status: {status_data['status']} - {status_data['progress']}")
            
            if status_data["status"] in ["succeeded", "failed"]:
                break
            await asyncio.sleep(2)
        
        # Get results
        resp = await client.get(
            f"http://127.0.0.1:8000/api/v1/jobs/{job_id}/results?format=json"
        )
        results = resp.json()
        
        # Save
        import json
        with open("results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"✅ Saved {len(results['results'])} genomes to results.json")

asyncio.run(extract_50_genomes())
```

## Output Files

### JSON Format (`metadata_{job_id}.json`):
```json
{
  "results": [
    {
      "accession": "AP039418",
      "version": "AP039418.1",
      "organism": "Escherichia coli",
      "definition": "...",
      "dblink": {
        "biosample": "SAMD00000001",
        "bioproject": "PRJDA12345"
      },
      "assembly": {
        "accession": "GCA_123456789.1",
        "name": "...",
        "level": "Complete Genome"
      },
      "references": [...]
    }
  ],
  "errors": []
}
```

### CSV Format:
Flattened view with columns: accession, version, organism, definition, biosample, bioproject, assembly_accession, etc.

## Troubleshooting

**Server not running?**
```powershell
python -m uvicorn src.ncbi_metadata_harvester.main:app --host 127.0.0.1 --port 8000
```

**Rate limiting?**
- Make sure your `.env` file has `NCBI_API_KEY` set
- With API key: 10 requests/second
- Without: 3 requests/second

**Job taking too long?**
- 50 genomes typically takes 2-5 minutes
- Check progress: `http://127.0.0.1:8000/api/v1/jobs/{job_id}`

**Errors in results?**
- Some accessions may not have assembly links
- Check the `errors` array in the JSON output
- Valid nuccore records still return metadata even without assembly info
