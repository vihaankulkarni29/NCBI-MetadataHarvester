"""Pydantic models for API requests and responses."""
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class AssemblyLevel(str, Enum):
    """Valid assembly levels for filtering."""

    COMPLETE_GENOME = "Complete Genome"
    CHROMOSOME = "Chromosome"
    SCAFFOLD = "Scaffold"
    CONTIG = "Contig"


class SourceDBPreference(str, Enum):
    """Preference for RefSeq vs GenBank assemblies."""

    REFSEQ = "RefSeq"
    GENBANK = "GenBank"
    EITHER = "Either"


class QueryFilters(BaseModel):
    """Filters for genome queries."""

    assembly_level: list[AssemblyLevel] | None = Field(
        default=None, description="Filter by assembly level (default: any)"
    )
    source_db_preference: SourceDBPreference = Field(
        default=SourceDBPreference.REFSEQ,
        description="Prefer RefSeq or GenBank assemblies",
    )
    latest_only: bool = Field(
        default=True, description="Return only latest assembly versions"
    )


class QueryJobRequest(BaseModel):
    """Request body for free-text genome query job."""

    organism: str = Field(..., description="Organism name (e.g., 'Escherichia coli')")
    keywords: list[str] | str | None = Field(
        default=None,
        description="Keywords to search for (e.g., 'Antimicrobial resistance')",
    )
    filters: QueryFilters = Field(default_factory=QueryFilters)
    limit: int = Field(default=20, ge=1, le=100, description="Max genomes to return")


class AccessionJobRequest(BaseModel):
    """Request body for accession list job."""

    accessions: list[str] = Field(
        ..., min_length=1, description="List of accessions (GCF_, GCA_, NC_, etc.)"
    )
    filters: QueryFilters = Field(default_factory=QueryFilters)


class JobStatus(str, Enum):
    """Possible job states."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobProgress(BaseModel):
    """Progress information for a job."""

    total: int = Field(default=0, description="Total items to process")
    completed: int = Field(default=0, description="Items completed")
    errors: int = Field(default=0, description="Items failed")


class JobResponse(BaseModel):
    """Response for job submission and status."""

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    progress: JobProgress | None = Field(default=None, description="Job progress")
    submitted_at: datetime = Field(..., description="Job submission timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    links: dict[str, str] | None = Field(
        default=None, description="Links to results when ready"
    )


class HealthResponse(BaseModel):
    """Response for health check."""

    status: Literal["ok"] = "ok"
