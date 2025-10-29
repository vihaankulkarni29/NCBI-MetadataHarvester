# How to Monitor and Verify Your Data Collection

## Quick Answer: Is My Data Being Collected?

**YES!** If the server is running and you submitted a job, data is being collected even if your terminal shows a timeout.

## Three Ways to Check Your Job

### 1. Quick Status Check (Recommended First)
```powershell
python src/check_job.py <job_id>
```

**Example:**
```powershell
python src/check_job.py 3ebce10c-02d3-448b-a224-4290ec9583cd
```

**Output shows:**
- Current status (running/succeeded/failed)
- Progress (29/50 completed = 58%)
- Number of errors
- If complete: automatically downloads results

### 2. Continuous Monitoring (Recommended for Long Jobs)
```powershell
python src/monitor_job.py <job_id>
```

**What it does:**
- Checks status every 10 seconds
- Shows live progress updates
- Estimates time remaining
- Auto-downloads results when complete
- Press Ctrl+C to stop (job keeps running in background)

### 3. Manual API Check
```powershell
# Check status
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/jobs/<job_id>"

# Get results (when succeeded)
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/jobs/<job_id>/results?format=json"
```

## Understanding Job Status

### Status Values

| Status | Meaning | Action |
|--------|---------|--------|
| `queued` | Job submitted, waiting to start | Wait a few seconds |
| `running` | Currently fetching metadata | Wait for completion |
| `succeeded` | All done! | Download results |
| `failed` | Error occurred | Check error messages |

### Progress Tracking

```json
"progress": {
  "total": 50,        // Total genomes to process
  "completed": 29,    // Successfully processed
  "errors": 1         // Failed/skipped
}
```

**Completion = completed + errors should eventually equal total**

## Where Are My Results?

Results are saved in the `results/` folder:

```
results/
├── metadata_<job_id>.json   (Full metadata with nested structure)
└── metadata_<job_id>.csv    (Flattened for Excel/spreadsheet)
```

## Verifying Data Quality

### 1. Check File Exists
```powershell
ls results/
```

### 2. Count Records in JSON
```powershell
$data = Get-Content results/metadata_<job_id>.json | ConvertFrom-Json
$data.results.Count  # Should match "completed" count
$data.errors.Count   # Should match "errors" count
```

### 3. View in Excel (CSV)
```powershell
start results/metadata_<job_id>.csv
```

### 4. Inspect Sample Data
```powershell
# Open in VS Code
code results/metadata_<job_id>.json

# View first record
$data = Get-Content results/metadata_<job_id>.json | ConvertFrom-Json
$data.results[0] | ConvertTo-Json -Depth 10
```

## Common Issues & Solutions

### Issue 1: "Job still running after timeout"
**Cause:** Default timeout was 10 minutes (too short for 50 genomes)

**Solution:** Job is still running in background! Use:
```powershell
python src/monitor_job.py <job_id>
```

**Fixed:** Updated `src/extract_metadata.py` timeout to 60 minutes

### Issue 2: "Cannot connect to server"
**Cause:** API server not running

**Solution:**
```powershell
# Start server in separate terminal
python -m uvicorn src.ncbi_metadata_harvester.main:app --host 127.0.0.1 --port 8000
```

### Issue 3: Some accessions have errors
**Cause:** Normal - some accessions may be:
- Withdrawn from NCBI
- Temporarily unavailable
- Network issues

**Solution:** Errors are logged in results JSON:
```json
"errors": [
  "Error processing CP184062.1: Server disconnected"
]
```

You can:
1. Retry just the failed accessions
2. Accept partial results (49/50 is 98% success rate!)

### Issue 4: Job seems stuck at same progress
**Cause:** Some genomes take longer (large records, slow NCBI response)

**Solution:** Be patient - each genome takes 30-60 seconds on average
- Check server logs for activity
- Use `src/monitor_job.py` to see updates in real-time

## Performance Expectations

| Genomes | Expected Time | Notes |
|---------|--------------|-------|
| 5 | 2-4 minutes | Quick test |
| 10 | 5-8 minutes | Small batch |
| 50 | 25-40 minutes | Standard batch (your case) |
| 100 | 50-80 minutes | Large batch |
| 500 | 4-7 hours | Very large |

**Factors affecting speed:**
- NCBI server load
- Genome size (complete genomes vs scaffolds)
- Network latency
- API key (10 rps vs 3 rps)

## Data Validation Checklist

After job completes, verify:

- [ ] JSON file exists in `results/`
- [ ] CSV file exists in `results/`
- [ ] JSON `results.length` matches expected count (minus errors)
- [ ] CSV has correct number of rows (excluding header)
- [ ] Sample records have all required fields:
  - [ ] accession
  - [ ] organism
  - [ ] definition
  - [ ] biosample (in dblink)
  - [ ] bioproject (in dblink)
  - [ ] references (at least 1)
- [ ] No duplicate accessions
- [ ] Errors are documented in `errors` array

## Example: Complete Workflow

```powershell
# 1. Start server (terminal 1)
python -m uvicorn src.ncbi_metadata_harvester.main:app --host 127.0.0.1 --port 8000

# 2. Submit job (terminal 2)
python src/extract_metadata.py 50

# If timeout occurs before completion...

# 3. Check if still running
python src/check_job.py <job_id_from_output>

# 4. Monitor to completion
python src/monitor_job.py <job_id_from_output>

# 5. Verify results
ls results/
Get-Content results/metadata_*.json | ConvertFrom-Json | Select-Object -ExpandProperty results | Measure-Object
```

## Getting Job ID

If you lost the job ID:

### From terminal output:
```
✅ Job created: 3ebce10c-02d3-448b-a224-4290ec9583cd
```

### From file listing:
```powershell
# Job ID is in the filename
ls results/metadata_*.json
# metadata_3ebce10c-02d3-448b-a224-4290ec9583cd.json
#          ^^^ this is the job ID ^^^
```

### From API (all jobs):
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/jobs"
```

## Pro Tips

1. **Use src/monitor_job.py for large batches** (50+ genomes)
   - Shows real-time progress
   - Estimates completion time
   - Auto-downloads when done

2. **Check sample data first** (5-10 genomes)
   - Verify metadata quality
   - Ensure fields are correct
   - Then scale to full batch

3. **Keep server terminal open**
   - See live logs
   - Catch errors immediately
   - Monitor memory/CPU

4. **Run overnight for huge batches** (500+ genomes)
   - Use src/monitor_job.py with output redirect
   - Check results in morning

5. **Back up results folder**
   - Jobs can take hours to complete
   - Results are saved immediately after each genome
   - Don't lose your data!

---

**Quick Reference Card:**

| Task | Command |
|------|---------|
| Check once | `python src/check_job.py <job_id>` |
| Monitor live | `python src/monitor_job.py <job_id>` |
| Extract data | `python src/extract_metadata.py 50` |
| View JSON | `code results/metadata_*.json` |
| Open CSV | `start results/metadata_*.csv` |
| Count records | `(Get-Content results/metadata_*.json \| ConvertFrom-Json).results.Count` |
