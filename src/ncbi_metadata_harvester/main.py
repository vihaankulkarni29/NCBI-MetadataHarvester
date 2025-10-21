import asyncio
import uuid

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from .csv_export import export_results_to_csv
from .job_processor import process_accession_job, process_query_job
from .job_store import get_job_store
from .models import (
    AccessionJobRequest,
    HealthResponse,
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
async def submit_query_job(request: QueryJobRequest, background_tasks: BackgroundTasks) -> JobResponse:
    """Submit a free-text genome metadata job."""
    job_id = str(uuid.uuid4())
    job_store = get_job_store()
    
    # Store job in registry
    job = await job_store.create_job(
        job_id=job_id,
        input_data=request.model_dump(),
        total=request.limit,
    )
    
    # Enqueue background task to process job
    background_tasks.add_task(process_query_job, job_id, request.model_dump())
    
    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        submitted_at=job.submitted_at,
        updated_at=job.updated_at,
    )


@app.post("/api/v1/jobs/accessions", status_code=202, response_model=JobResponse)
async def submit_accession_job(request: AccessionJobRequest, background_tasks: BackgroundTasks) -> JobResponse:
    """Submit an accession list metadata job."""
    job_id = str(uuid.uuid4())
    job_store = get_job_store()
    
    # Store job in registry
    job = await job_store.create_job(
        job_id=job_id,
        input_data=request.model_dump(),
        total=len(request.accessions),
    )
    
    # Enqueue background task to process job
    background_tasks.add_task(process_accession_job, job_id, request.model_dump())
    
    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        submitted_at=job.submitted_at,
        updated_at=job.updated_at,
    )


@app.get("/api/v1/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str) -> JobResponse:
    """Get job status and progress."""
    job_store = get_job_store()
    job = await job_store.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Build links if job succeeded
    links = None
    if job.status == JobStatus.SUCCEEDED:
        links = {
            "results_json": f"/api/v1/jobs/{job_id}/results?format=json",
            "results_csv": f"/api/v1/jobs/{job_id}/results?format=csv",
        }
    
    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        submitted_at=job.submitted_at,
        updated_at=job.updated_at,
        links=links,
    )


@app.get("/api/v1/jobs/{job_id}/results")
async def get_job_results(job_id: str, format: str = "json"):
    """Get job results in JSON or CSV format."""
    job_store = get_job_store()
    job = await job_store.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.SUCCEEDED:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not ready. Current status: {job.status}",
        )
    
    if format == "json":
        return {"results": job.results, "errors": job.errors}
    elif format == "csv":
        csv_content = export_results_to_csv(job.results)
        return PlainTextResponse(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=job_{job_id}_results.csv"}
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'json' or 'csv'.")
