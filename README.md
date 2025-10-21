# NCBI-MetadataHarvester

A Python-based tool that extracts high-quality genome metadata from NCBI using either a free-text query (organism + keywords + filters + limit) or a user-provided accession list.

## ✨ Features
- **Query-based search**: "Escherichia coli K-12" with filters (assembly level, RefSeq, latest)
- **Accession lists**: Process lists of GCF_/GCA_ assemblies or NC_/NZ_/CP_ nucleotide sequences
- **Complete metadata**: LOCUS, DEFINITION, ACCESSION, VERSION, DBLINK (BioSample, BioProject), KEYWORDS, SOURCE, ORGANISM, REFERENCES (AUTHORS, TITLE, JOURNAL, PUBMED)
- **Multiple formats**: JSON (full metadata) and CSV (spreadsheet-friendly)
- **Async processing**: Background jobs with progress tracking
- **NCBI-friendly**: Rate limiting (10 req/s with API key), retry logic with exponential backoff

## 🚀 Quick Start: Extract Metadata from Your Accession List

**See detailed guide:** [`HOW_TO_EXTRACT.md`](HOW_TO_EXTRACT.md)

### 1. Start the server (separate terminal):
```powershell
python -m uvicorn src.ncbi_metadata_harvester.main:app --host 127.0.0.1 --port 8000
```

### 2. Extract first 50 genomes from `accession_list.txt`:
```powershell
python extract_metadata.py 50
```

Results are saved to `results/` folder in both JSON and CSV formats!

**Time estimate:** ~30-40 minutes for 50 genomes

## 📚 Documentation

### User Guides
- **[HOW_TO_EXTRACT.md](HOW_TO_EXTRACT.md)** - Step-by-step guide to extract metadata from your accession list
- **[EXTRACTION_GUIDE.md](EXTRACTION_GUIDE.md)** - Detailed methods (script, PowerShell, Python)

### Design Documents
- [docs/product-spec.md](docs/product-spec.md) — Requirements, use cases, acceptance criteria
- [docs/data-sources.md](docs/data-sources.md) — E-utilities vs Datasets, rate limits
- [docs/metadata-schema.md](docs/metadata-schema.md) — JSON schema and GenBank field mapping
- [docs/search-and-resolution.md](docs/search-and-resolution.md) — Query building and accession resolution
- [docs/architecture.md](docs/architecture.md) — SaaS architecture (FastAPI, workers, cache)
- [docs/api.md](docs/api.md) — Public API contract and examples
- [docs/rate-limits-retries.md](docs/rate-limits-retries.md) — Throttling, batching, backoff
- [docs/data-quality.md](docs/data-quality.md) — Selection rules and validation
- [docs/deployment.md](docs/deployment.md) — Deployment and operations plan
- [docs/roadmap.md](docs/roadmap.md) — Phased delivery plan

## 🛠️ Setup for Development

### 1. Clone and setup environment
```powershell
# Clone the repository
git clone https://github.com/vihaankulkarni29/NCBI-MetadataHarvester.git
cd NCBI-MetadataHarvester

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure NCBI credentials
Create a `.env` file (copy from `.env.example`):
```
NCBI_API_KEY=your_ncbi_api_key_here
NCBI_EMAIL=your_email@example.com
NCBI_TOOL=ncbi-metadata-harvester
```

**Get an API key:** https://www.ncbi.nlm.nih.gov/account/settings/

### 3. Start the server
```powershell
python -m uvicorn src.ncbi_metadata_harvester.main:app --host 127.0.0.1 --port 8000
```

Server will be available at: http://127.0.0.1:8000

### 4. Run tests
```powershell
pytest tests/ -v
```

All 24 tests should pass ✅

## 🎯 Usage Examples

### Extract from accession list
```powershell
python extract_metadata.py 50
```

### Test with known accessions
```powershell
python test_comprehensive.py
```

### API Examples

**Submit a query-based job:**
```powershell
$body = @{
    organism = "Escherichia coli K-12"
    filters = @{
        assembly_level = @("Complete Genome")
        source_db_preference = "RefSeq"
        latest_only = $true
    }
    limit = 5
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/jobs/query" `
    -Method POST -Body $body -ContentType "application/json"
```

**Submit an accession list job:**
```powershell
$body = @{
    accessions = @("GCF_000005845.2", "NC_003197.2")
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/jobs/accessions" `
    -Method POST -Body $body -ContentType "application/json"
```

**Check job status:**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/jobs/{job_id}"
```

**Get results:**
```powershell
# JSON format
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/jobs/{job_id}/results?format=json"

# CSV format
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/jobs/{job_id}/results?format=csv"
```

## 📊 Output Formats

### JSON
Complete metadata with nested structures:
```json
{
  "results": [
    {
      "locus": "NC_000913",
      "definition": "Escherichia coli str. K-12 substr. MG1655, complete genome",
      "accession": "NC_000913",
      "version": "NC_000913.3",
      "dblink": {
        "biosample": "SAMN02604091",
        "bioproject": "PRJNA57779"
      },
      "organism": "Escherichia coli str. K-12 substr. MG1655",
      "taxonomy": ["Bacteria", "Pseudomonadota", ...],
      "references": [
        {
          "authors": "Riley M., et al.",
          "title": "Escherichia coli K-12: a cooperatively developed...",
          "journal": "Nucleic Acids Res. 34 (1), 1-9 (2006)",
          "pubmed": "16397293"
        }
      ],
      "assembly": {
        "accession": "GCF_000005845.2",
        "name": "ASM584v2",
        "level": "Complete Genome"
      }
    }
  ],
  "errors": []
}
```

### CSV
Flattened spreadsheet format with columns:
- `accession`, `version`, `locus`, `definition`
- `organism`, `source`, `biosample`, `bioproject`
- `keywords`, `taxonomy`
- `assembly_accession`, `assembly_name`, `assembly_level`
- `ref_authors`, `ref_title`, `ref_journal`, `ref_pubmed`

## ⚡ Performance

- **Rate limiting**: 3 req/s (without API key) or 10 req/s (with API key)
- **Retry logic**: Exponential backoff on 429/5xx errors
- **Processing time**: ~30-50 seconds per genome (includes NCBI delays)
- **Batch estimates**:
  - 5 genomes: ~4 minutes
  - 50 genomes: ~30-40 minutes
  - 500 genomes: ~5-7 hours

## 🧪 Testing

Unit tests cover:
- HTTP client retry logic
- Rate limiting
- Job store operations
- API endpoints
- GenBank parsing

```powershell
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_http_client.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/ -v`
5. Submit a pull request

## 📧 Support

For issues or questions, please open an issue on GitHub.

---

**Ready to extract genome metadata? See [HOW_TO_EXTRACT.md](HOW_TO_EXTRACT.md) to get started!** 🚀
Then open http://127.0.0.1:8000/healthz