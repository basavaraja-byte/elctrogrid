"""Technician management API routes."""

from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import AvailabilityStatus, ScheduleVersionStatus
from app.models.schedule import ScheduleVersion
from app.schemas.technician import (
    TechnicianAvailabilityPatch,
    TechnicianCreate,
    TechnicianResponse,
    TechnicianUpdate,
    TechnicianWindowAvailabilityResponse,
)
from app.services.technician_service import TechnicianService

router = APIRouter(prefix="/technicians", tags=["Technicians"])


@router.post(
    "",
    response_model=TechnicianResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_technician(
    payload: TechnicianCreate,
    db: Session = Depends(get_db),
) -> TechnicianResponse:
    """Create a new electrician technician."""
    tech = TechnicianService.create_technician(db, payload)
    return TechnicianResponse.model_validate(tech)


@router.get(
    "",
    response_model=list[TechnicianResponse],
)
def list_technicians(
    availability_status: AvailabilityStatus | None = Query(default=None),
    skill: str | None = Query(default=None),
    service_zone: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    available_from: datetime | None = Query(default=None),
    available_until: datetime | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[TechnicianResponse]:
    """List technicians with optional skill, zone, active status, and time-window filters."""
    technicians = TechnicianService.list_technicians(
        db,
        availability_status=availability_status,
        skill=skill,
        service_zone=service_zone,
        is_active=is_active,
        available_from=available_from,
        available_until=available_until,
        skip=skip,
        limit=limit,
    )
    return [TechnicianResponse.model_validate(t) for t in technicians]


@router.get(
    "/{technician_id}",
    response_model=TechnicianResponse,
)
def get_technician(
    technician_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> TechnicianResponse:
    """Get a single technician by ID."""
    tech = TechnicianService.get_technician_by_id(db, technician_id)
    return TechnicianResponse.model_validate(tech)


@router.put(
    "/{technician_id}",
    response_model=TechnicianResponse,
)
def update_technician(
    technician_id: uuid.UUID,
    payload: TechnicianUpdate,
    db: Session = Depends(get_db),
) -> TechnicianResponse:
    """Full update of a technician record."""
    tech = TechnicianService.update_technician(db, technician_id, payload)
    return TechnicianResponse.model_validate(tech)


@router.patch(
    "/{technician_id}/availability",
    response_model=TechnicianResponse,
)
def patch_technician_availability(
    technician_id: uuid.UUID,
    payload: TechnicianAvailabilityPatch,
    db: Session = Depends(get_db),
) -> TechnicianResponse:
    """Update a technician's availability status, active state, and optional break/unavailable window."""
    tech = TechnicianService.patch_availability(db, technician_id, payload)
    return TechnicianResponse.model_validate(tech)


@router.get(
    "/{technician_id}/availability-check",
    response_model=TechnicianWindowAvailabilityResponse,
)
def check_technician_window_availability(
    technician_id: uuid.UUID,
    window_start: datetime = Query(...),
    window_end: datetime = Query(...),
    db: Session = Depends(get_db),
) -> TechnicianWindowAvailabilityResponse:
    """Evaluate time-aware availability of a technician during [window_start, window_end)."""
    tech = TechnicianService.get_technician_by_id(db, technician_id)
    active_version = db.scalar(
        select(ScheduleVersion).where(
            ScheduleVersion.status == ScheduleVersionStatus.ACTIVE.value
        )
    )
    existing_assignments = active_version.assignments if active_version else []
    return TechnicianService.check_availability_in_window(
        tech, window_start, window_end, existing_assignments
    )

