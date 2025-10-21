import uuid
from datetime import datetime, timezone

from fastapi import FastAPI

from .models import (
    AccessionJobRequest,
    HealthResponse,
    JobProgress,
    JobResponse,
    JobStatus,
    QueryJobRequest,
)

app = FastAPI(title="NCBI Metadata Harvester", version="0.1.0")


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok")


@app.post("/api/v1/jobs/query", status_code=202, response_model=JobResponse)
async def submit_query_job(request: QueryJobRequest) -> JobResponse:
    """Submit a free-text genome metadata job."""
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    return JobResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        progress=JobProgress(total=request.limit, completed=0, errors=0),
        submitted_at=now,
        updated_at=now,
    )


@app.post("/api/v1/jobs/accessions", status_code=202, response_model=JobResponse)
async def submit_accession_job(request: AccessionJobRequest) -> JobResponse:
    """Submit an accession list metadata job."""
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    return JobResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        progress=JobProgress(total=len(request.accessions), completed=0, errors=0),
        submitted_at=now,
        updated_at=now,
    )
