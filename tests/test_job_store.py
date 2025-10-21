"""Tests for job store and job management endpoints."""
import pytest
from fastapi.testclient import TestClient

from ncbi_metadata_harvester.job_store import JobStore, get_job_store
from ncbi_metadata_harvester.main import app
from ncbi_metadata_harvester.models import JobStatus

client = TestClient(app)


class TestJobStore:
    """Tests for JobStore."""

    @pytest.mark.asyncio
    async def test_create_and_get_job(self):
        """Test creating and retrieving a job."""
        store = JobStore()
        job = await store.create_job(
            job_id="test-123",
            input_data={"organism": "E. coli"},
            total=10,
        )

        assert job.job_id == "test-123"
        assert job.status == JobStatus.QUEUED
        assert job.progress.total == 10
        assert job.progress.completed == 0

        retrieved = await store.get_job("test-123")
        assert retrieved is not None
        assert retrieved.job_id == "test-123"

    @pytest.mark.asyncio
    async def test_update_job_status(self):
        """Test updating job status."""
        store = JobStore()
        await store.create_job(job_id="test-456", input_data={}, total=5)

        await store.update_job_status("test-456", JobStatus.RUNNING)
        job = await store.get_job("test-456")
        assert job.status == JobStatus.RUNNING

    @pytest.mark.asyncio
    async def test_add_result_updates_progress(self):
        """Test adding results updates progress."""
        store = JobStore()
        await store.create_job(job_id="test-789", input_data={}, total=3)

        await store.add_job_result("test-789", {"accession": "NC_123"})
        await store.add_job_result("test-789", {"accession": "NC_456"})

        job = await store.get_job("test-789")
        assert job.progress.completed == 2
        assert len(job.results) == 2

    @pytest.mark.asyncio
    async def test_add_error_updates_progress(self):
        """Test adding errors updates progress."""
        store = JobStore()
        await store.create_job(job_id="test-error", input_data={}, total=5)

        await store.add_job_error("test-error", "Failed to fetch accession")
        await store.add_job_error("test-error", "Timeout")

        job = await store.get_job("test-error")
        assert job.progress.errors == 2
        assert len(job.errors) == 2


class TestJobEndpoints:
    """Tests for job management endpoints."""

    def test_submit_query_job_creates_job(self):
        """Test submitting a query job creates it in the store."""
        payload = {"organism": "Salmonella", "limit": 10}
        resp = client.post("/api/v1/jobs/query", json=payload)
        
        assert resp.status_code == 202
        data = resp.json()
        job_id = data["job_id"]

        # Verify job is retrievable
        status_resp = client.get(f"/api/v1/jobs/{job_id}")
        assert status_resp.status_code == 200
        assert status_resp.json()["job_id"] == job_id
        assert status_resp.json()["status"] == "queued"

    def test_get_job_status_not_found(self):
        """Test getting status for non-existent job returns 404."""
        resp = client.get("/api/v1/jobs/nonexistent-job-id")
        assert resp.status_code == 404

    def test_get_results_job_not_ready(self):
        """Test getting results when job is not succeeded returns 400."""
        payload = {"organism": "Bacillus", "limit": 5}
        submit_resp = client.post("/api/v1/jobs/query", json=payload)
        job_id = submit_resp.json()["job_id"]

        # Job is queued, not succeeded
        results_resp = client.get(f"/api/v1/jobs/{job_id}/results")
        assert results_resp.status_code == 400
        assert "not ready" in results_resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_results_when_succeeded(self):
        """Test getting results when job is succeeded."""
        # Manually create a succeeded job
        store = get_job_store()
        job = await store.create_job(
            job_id="test-success",
            input_data={"organism": "E. coli"},
            total=2,
        )
        await store.add_job_result("test-success", {"accession": "NC_123", "organism": "E. coli"})
        await store.add_job_result("test-success", {"accession": "NC_456", "organism": "E. coli"})
        await store.update_job_status("test-success", JobStatus.SUCCEEDED)

        # Get status endpoint should include links
        status_resp = client.get("/api/v1/jobs/test-success")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["status"] == "succeeded"
        assert "links" in data
        assert "results_json" in data["links"]

        # Get results
        results_resp = client.get("/api/v1/jobs/test-success/results?format=json")
        assert results_resp.status_code == 200
        results = results_resp.json()
        assert len(results["results"]) == 2
        assert results["results"][0]["accession"] == "NC_123"

    @pytest.mark.asyncio
    async def test_get_results_invalid_format(self):
        """Test getting results with invalid format returns 400."""
        # Create a succeeded job so format validation is reached
        store = get_job_store()
        await store.create_job(job_id="test-format", input_data={"organism": "Test"}, total=1)
        await store.update_job_status("test-format", JobStatus.SUCCEEDED)

        results_resp = client.get("/api/v1/jobs/test-format/results?format=xml")
        assert results_resp.status_code == 400
        assert "Invalid format" in results_resp.json()["detail"]
