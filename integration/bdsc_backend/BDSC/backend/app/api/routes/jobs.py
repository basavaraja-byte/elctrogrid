"""Electrical Service Job management API routes."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import JobPriority, JobStatus
from app.schemas.job import JobCreate, JobResponse, JobStatusPatch, JobUpdate
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
) -> JobResponse:
    """Create a new electrical service job."""
    job = JobService.create_job(db, payload)
    return JobResponse.model_validate(job)


@router.get(
    "",
    response_model=list[JobResponse],
)
def list_jobs(
    customer_id: uuid.UUID | None = Query(default=None),
    status: JobStatus | None = Query(default=None),
    priority: JobPriority | None = Query(default=None),
    service_zone: str | None = Query(default=None),
    job_type: str | None = Query(default=None),
    required_skill: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[JobResponse]:
    """List electrical service jobs with optional filters."""
    jobs = JobService.list_jobs(
        db,
        customer_id=customer_id,
        status=status,
        priority=priority,
        service_zone=service_zone,
        job_type=job_type,
        required_skill=required_skill,
        skip=skip,
        limit=limit,
    )
    return [JobResponse.model_validate(j) for j in jobs]


@router.get(
    "/{job_id}",
    response_model=JobResponse,
)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> JobResponse:
    """Retrieve a single electrical service job by ID."""
    job = JobService.get_job_by_id(db, job_id)
    return JobResponse.model_validate(job)


@router.put(
    "/{job_id}",
    response_model=JobResponse,
)
def update_job(
    job_id: uuid.UUID,
    payload: JobUpdate,
    db: Session = Depends(get_db),
) -> JobResponse:
    """Full update of an electrical service job."""
    job = JobService.update_job(db, job_id, payload)
    return JobResponse.model_validate(job)


@router.patch(
    "/{job_id}/status",
    response_model=JobResponse,
)
def patch_job_status(
    job_id: uuid.UUID,
    payload: JobStatusPatch,
    db: Session = Depends(get_db),
) -> JobResponse:
    """Transition job status enforcing the canonical state machine."""
    job = JobService.patch_job_status(db, job_id, payload)
    return JobResponse.model_validate(job)


@router.delete(
    "/{job_id}",
)
def delete_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Delete an electrical service job (blocked if IN_PROGRESS or COMPLETED)."""
    return JobService.delete_job(db, job_id)

