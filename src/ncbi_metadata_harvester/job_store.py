"""In-memory job store and management."""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .models import JobProgress, JobStatus


@dataclass
class Job:
    """Represents a metadata harvesting job."""

    job_id: str
    status: JobStatus
    progress: JobProgress
    submitted_at: datetime
    updated_at: datetime
    input_data: dict[str, Any]
    results: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def update_progress(self, completed: int | None = None, errors: int | None = None) -> None:
        """Update job progress and timestamp."""
        if completed is not None:
            self.progress.completed = completed
        if errors is not None:
            self.progress.errors = errors
        self.updated_at = datetime.now(timezone.utc)

    def update_status(self, status: JobStatus) -> None:
        """Update job status and timestamp."""
        self.status = status
        self.updated_at = datetime.now(timezone.utc)

    def add_result(self, result: dict[str, Any]) -> None:
        """Add a result to the job."""
        self.results.append(result)
        self.update_progress(completed=len(self.results))

    def add_error(self, error: str) -> None:
        """Add an error to the job."""
        self.errors.append(error)
        self.update_progress(errors=len(self.errors))


class JobStore:
    """In-memory job storage and registry."""

    def __init__(self):
        """Initialize job store."""
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()

    async def create_job(
        self, job_id: str, input_data: dict[str, Any], total: int
    ) -> Job:
        """
        Create a new job.

        Args:
            job_id: Unique job identifier
            input_data: Job input parameters
            total: Total items to process

        Returns:
            Created job object
        """
        async with self._lock:
            now = datetime.now(timezone.utc)
            job = Job(
                job_id=job_id,
                status=JobStatus.QUEUED,
                progress=JobProgress(total=total, completed=0, errors=0),
                submitted_at=now,
                updated_at=now,
                input_data=input_data,
            )
            self._jobs[job_id] = job
            return job

    async def get_job(self, job_id: str) -> Job | None:
        """
        Retrieve a job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job object or None if not found
        """
        async with self._lock:
            return self._jobs.get(job_id)

    async def update_job_status(self, job_id: str, status: JobStatus) -> None:
        """
        Update job status.

        Args:
            job_id: Job identifier
            status: New status
        """
        async with self._lock:
            if job := self._jobs.get(job_id):
                job.update_status(status)

    async def update_job_progress(
        self, job_id: str, completed: int | None = None, errors: int | None = None
    ) -> None:
        """
        Update job progress.

        Args:
            job_id: Job identifier
            completed: Completed items count
            errors: Error count
        """
        async with self._lock:
            if job := self._jobs.get(job_id):
                job.update_progress(completed=completed, errors=errors)

    async def add_job_result(self, job_id: str, result: dict[str, Any]) -> None:
        """
        Add a result to a job.

        Args:
            job_id: Job identifier
            result: Result data
        """
        async with self._lock:
            if job := self._jobs.get(job_id):
                job.add_result(result)

    async def add_job_error(self, job_id: str, error: str) -> None:
        """
        Add an error to a job.

        Args:
            job_id: Job identifier
            error: Error message
        """
        async with self._lock:
            if job := self._jobs.get(job_id):
                job.add_error(error)

    async def list_jobs(self, limit: int = 100) -> list[Job]:
        """
        List recent jobs.

        Args:
            limit: Maximum jobs to return

        Returns:
            List of jobs, newest first
        """
        async with self._lock:
            jobs = sorted(
                self._jobs.values(), key=lambda j: j.submitted_at, reverse=True
            )
            return jobs[:limit]


# Global job store instance
_job_store: JobStore | None = None


def get_job_store() -> JobStore:
    """Get or create the global job store instance."""
    global _job_store
    if _job_store is None:
        _job_store = JobStore()
    return _job_store
