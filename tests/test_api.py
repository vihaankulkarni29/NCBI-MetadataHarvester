"""Tests for API endpoints and request/response models."""
from fastapi.testclient import TestClient

from ncbi_metadata_harvester.main import app

client = TestClient(app)


def test_healthz():
    """Test health check endpoint."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_submit_query_job():
    """Test POST /api/v1/jobs/query with minimal request."""
    payload = {
        "organism": "Escherichia coli",
        "keywords": ["Antimicrobial resistance"],
        "filters": {"assembly_level": ["Complete Genome"]},
        "limit": 20,
    }
    resp = client.post("/api/v1/jobs/query", json=payload)
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert data["progress"]["total"] == 20
    assert data["progress"]["completed"] == 0


def test_submit_query_job_defaults():
    """Test POST /api/v1/jobs/query with defaults."""
    payload = {"organism": "Salmonella enterica"}
    resp = client.post("/api/v1/jobs/query", json=payload)
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"
    assert data["progress"]["total"] == 20  # default limit


def test_submit_accession_job():
    """Test POST /api/v1/jobs/accessions."""
    payload = {
        "accessions": ["GCF_000005845.2", "NC_000913.3", "GCA_000008865.1"],
    }
    resp = client.post("/api/v1/jobs/accessions", json=payload)
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert data["progress"]["total"] == 3
    assert data["progress"]["completed"] == 0


def test_submit_accession_job_empty_list():
    """Test POST /api/v1/jobs/accessions with empty list fails validation."""
    payload = {"accessions": []}
    resp = client.post("/api/v1/jobs/accessions", json=payload)
    assert resp.status_code == 422  # Unprocessable Entity


def test_query_job_invalid_limit():
    """Test POST /api/v1/jobs/query with out-of-range limit."""
    payload = {"organism": "Bacillus subtilis", "limit": 200}
    resp = client.post("/api/v1/jobs/query", json=payload)
    assert resp.status_code == 422  # exceeds max 100
