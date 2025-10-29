# ✅ YES! You can extract metadata for the first 50 genomes (or any number)

## 🚀 Quick Answer

**Run this command:**
```powershell
python src/extract_metadata.py 50
```

That's it! The script will:
1. Read the first 50 accessions from `accession_list.txt`
2. Submit them to the NCBI Metadata Harvester API
3. Wait for processing to complete (shows progress)
4. Save results to `results/` folder in both JSON and CSV formats

## ⏱️ Expected Time
- **5 genomes**: ~4 minutes (just tested ✅)
- **50 genomes**: ~30-40 minutes (estimated)
- The script shows live progress, so you can monitor it

## 📋 Prerequisites

### 1. Make sure the server is running
Open a **separate terminal** and run:
```powershell
python -m uvicorn src.ncbi_metadata_harvester.main:app --host 127.0.0.1 --port 8000
```

Keep this terminal open while the extraction runs.

### 2. Verify your `.env` file exists
Should contain:
```
NCBI_API_KEY=your_actual_api_key_here
NCBI_EMAIL=your_email@example.com
NCBI_TOOL=ncbi-metadata-harvester
```

## 📊 What You'll Get

The script creates a `results/` folder with two files:

### 1. JSON file (`metadata_{job_id}.json`)
Complete metadata for each genome including:
- ✅ LOCUS
- ✅ DEFINITION
- ✅ ACCESSION & VERSION
- ✅ DBLINK (BioSample, BioProject)
- ✅ KEYWORDS
- ✅ SOURCE & ORGANISM
- ✅ TAXONOMY
- ✅ REFERENCES (Authors, Title, Journal, PubMed)
- ✅ ASSEMBLY info (if available)

**Example structure:**
```json
{
  "results": [
    {
      "locus": "AP039418",
      "definition": "Escherichia coli BroCaecum-55 DNA, complete genome",
      "accession": "AP039418",
      "version": "AP039418.1",
      "dblink": {
        "biosample": "SAMD00874696",
        "bioproject": "PRJDB19974"
      },
      "organism": "Escherichia coli",
      "taxonomy": ["Bacteria", "Pseudomonadota", ...],
      "references": [
        {
          "authors": "Kawano,K., Masaki,T., ...",
          "title": "Persistence of Colistin Resistance...",
          "journal": "Antibiotics (Basel) 14 (4), 360 (2025)",
          "pubmed": "40298502"
        }
      ]
    }
  ],
  "errors": []
}
```

### 2. CSV file (`metadata_{job_id}.csv`)
Spreadsheet-friendly format with flattened fields:
- `accession`, `version`, `locus`
- `definition`, `organism`, `source`
- `biosample`, `bioproject`
- `keywords`, `taxonomy`
- `assembly_accession`, `assembly_name`, `assembly_level`
- `ref_authors`, `ref_title`, `ref_journal`, `ref_pubmed` (first reference)

**Open directly in Excel or Google Sheets!**

## 🎯 Usage Examples

### Extract first 50 (default):
```powershell
python src/extract_metadata.py
```

### Extract first 100:
```powershell
python src/extract_metadata.py 100
```

### Extract just 10 for testing:
```powershell
python src/extract_metadata.py 10
```

## 📈 Live Progress Example

When you run the script, you'll see:
```
🔬 NCBI Metadata Harvester - Batch Extraction
======================================================================
📖 Reading accessions from accession_list.txt...
✅ Found 61160 total accessions
🎯 Processing first 50 accessions

🚀 Submitting job to http://127.0.0.1:8000...
✅ Job created: abc123-def456-...
   Status: queued

⏳ Waiting for job to complete...
   (This may take several minutes for 50 genomes)

   [10s] Status: running
         Progress: 3/50
         Errors: 0
...............
   [120s] Status: running
         Progress: 15/50
         Errors: 0
...

✅ Job succeeded!
📥 Downloading results...
✅ Saved JSON: results\metadata_abc123.json
✅ Saved CSV: results\metadata_abc123.csv

======================================================================
📊 SUMMARY
======================================================================
Total accessions requested: 50
Successfully processed: 48
Errors encountered: 2

✅ Sample results (first 3):
  [1] AP039418 - Escherichia coli
      BioSample: SAMD00874696
      BioProject: PRJDB19974
  ...
```

## ⚠️ Troubleshooting

### Error: "Cannot connect to the API server"
**Solution:** Start the server first:
```powershell
python -m uvicorn src.ncbi_metadata_harvester.main:app --host 127.0.0.1 --port 8000
```

### Processing is slow
**This is normal!** Each genome requires:
1. Fetching GenBank record from NCBI (~2-3 seconds)
2. Parsing metadata
3. Linking to assembly database (if available)

With rate limiting (10 req/sec with API key), 50 genomes takes ~30-40 minutes.

### Some accessions have errors
**This is OK!** Some reasons:
- Accession might be withdrawn
- No assembly link available
- Temporary NCBI API issues

The script will:
- Continue processing remaining accessions
- List errors in the `errors` array
- Still save successful results

## 🎁 Bonus: Process ALL 61,000+ Accessions

Want to process your entire list? You can!

**Option 1: Process in batches**
```powershell
# Batch 1: First 100
python src/extract_metadata.py 100

# Batch 2: Next 100 (modify script to skip first 100)
# Batch 3: Next 100
# etc.
```

**Option 2: One big job (will take ~20-30 hours)**
```powershell
python src/extract_metadata.py 61160
```

**Recommendation:** Start with 50, verify the results look good, then scale up!

## 📚 More Details

See `docs/EXTRACTION_GUIDE.md` for:
- Alternative methods (PowerShell, Python code)
- API endpoint details
- Manual job submission
- Output file formats

---

**Ready? Let's extract those genomes! 🚀**

```powershell
# Step 1: Start server (in separate terminal)
python -m uvicorn src.ncbi_metadata_harvester.main:app --host 127.0.0.1 --port 8000

# Step 2: Run extraction (in this terminal)
python src/extract_metadata.py 50
```