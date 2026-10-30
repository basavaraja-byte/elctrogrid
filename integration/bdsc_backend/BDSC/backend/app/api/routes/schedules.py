"""Shared Scheduling, Recovery, Human Approval, Candidate Ranking, and Metrics API routes."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import ScheduleVersionStatus, SchedulingRunType
from app.schemas.schedule import (
    CandidateRankingRequest,
    CandidateRankingResponse,
    ScheduleApproveRequest,
    ScheduleComparisonResponse,
    ScheduleGenerateRequest,
    ScheduleGenerationResponse,
    ScheduleMetricsResponse,
    ScheduleRejectRequest,
    ScheduleValidationRequest,
    ScheduleValidationResponse,
    ScheduleVersionResponse,
    SchedulingRunResponse,
)
from app.services.metrics_service import MetricsService
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedules", tags=["Schedules"])


@router.post(
    "/generate",
    response_model=ScheduleGenerationResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_schedule(
    payload: ScheduleGenerateRequest,
    db: Session = Depends(get_db),
) -> ScheduleGenerationResponse:
    """Trigger or persist a schedule generation run (INITIAL, OPTIMIZATION, or RECOVERY)."""
    return ScheduleService.generate_schedule(db, payload)


@router.get(
    "/current",
    response_model=ScheduleGenerationResponse,
)
def get_current_active_schedule(
    db: Session = Depends(get_db),
) -> ScheduleGenerationResponse:
    """Retrieve the currently ACTIVE production schedule version."""
    return ScheduleService.get_current_schedule(db)


@router.get(
    "/versions",
    response_model=list[ScheduleVersionResponse],
)
def list_schedule_versions(
    status: ScheduleVersionStatus | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[ScheduleVersionResponse]:
    """List historical, draft, rejected, and active schedule versions."""
    versions = ScheduleService.list_schedule_versions(
        db, status=status, skip=skip, limit=limit
    )
    return [ScheduleVersionResponse.model_validate(v) for v in versions]


@router.get(
    "/runs",
    response_model=list[SchedulingRunResponse],
)
def list_scheduling_runs(
    run_type: SchedulingRunType | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[SchedulingRunResponse]:
    """List scheduling execution runs."""
    runs = ScheduleService.list_scheduling_runs(
        db, run_type=run_type, skip=skip, limit=limit
    )
    return [SchedulingRunResponse.model_validate(r) for r in runs]


@router.get(
    "/runs/{run_id}",
    response_model=SchedulingRunResponse,
)
def get_scheduling_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> SchedulingRunResponse:
    """Retrieve a specific scheduling run by ID."""
    run = ScheduleService.get_scheduling_run_by_id(db, run_id)
    return SchedulingRunResponse.model_validate(run)


@router.post(
    "/rank-candidates",
    response_model=CandidateRankingResponse,
)
def rank_technician_candidates(
    payload: CandidateRankingRequest,
    db: Session = Depends(get_db),
) -> CandidateRankingResponse:
    """Rank feasible technicians for a job using ConstraintValidator and weighted heuristic scoring."""
    return ScheduleService.rank_candidates(db, payload)


@router.post(
    "/validate",
    response_model=ScheduleValidationResponse,
)
def validate_schedule_proposal(
    payload: ScheduleValidationRequest,
    db: Session = Depends(get_db),
) -> ScheduleValidationResponse:
    """Validate a proposed assignment bundle against centralized hard constraints and recovery protection."""
    return ScheduleService.validate_proposed_schedule(db, payload)


@router.get(
    "/{schedule_id}",
    response_model=ScheduleGenerationResponse,
)
def get_schedule_by_id(
    schedule_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ScheduleGenerationResponse:
    """Retrieve a specific schedule version with assignments, SLA risks, and audit logs."""
    return ScheduleService.get_schedule_by_id(db, schedule_id)


@router.get(
    "/{schedule_id}/metrics",
    response_model=ScheduleMetricsResponse,
)
def get_schedule_metrics(
    schedule_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ScheduleMetricsResponse:
    """Calculate actual schedule metrics, SLA compliance, workload distribution, and constraint violations."""
    return MetricsService.calculate_schedule_metrics(db, schedule_id)


@router.post(
    "/{schedule_id}/approve",
    response_model=ScheduleGenerationResponse,
)
def approve_schedule_proposal(
    schedule_id: uuid.UUID,
    payload: ScheduleApproveRequest,
    db: Session = Depends(get_db),
) -> ScheduleGenerationResponse:
    """Operations Manager approval endpoint to validate and activate a DRAFT schedule proposal."""
    return ScheduleService.approve_schedule(db, schedule_id, payload)


@router.post(
    "/{schedule_id}/reject",
    response_model=ScheduleGenerationResponse,
)
def reject_schedule_proposal(
    schedule_id: uuid.UUID,
    payload: ScheduleRejectRequest,
    db: Session = Depends(get_db),
) -> ScheduleGenerationResponse:
    """Operations Manager rejection endpoint for a DRAFT schedule proposal."""
    return ScheduleService.reject_schedule(db, schedule_id, payload)


@router.get(
    "/{schedule_id}/compare/{other_schedule_id}",
    response_model=ScheduleComparisonResponse,
)
def compare_schedule_versions(
    schedule_id: uuid.UUID,
    other_schedule_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ScheduleComparisonResponse:
    """Calculate before-and-after metrics and assignment diffs between two schedule versions."""
    return MetricsService.compare_schedules(db, schedule_id, other_schedule_id)

