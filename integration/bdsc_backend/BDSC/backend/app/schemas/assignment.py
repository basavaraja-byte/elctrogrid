"""Pydantic v2 schemas for Assignments."""

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import AssignmentStatus
from app.utils.validators import ensure_timezone_aware


class ProposedAssignmentInput(BaseModel):
    """Input schema for an assignment proposed by a scheduler or recovery engine."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "11bc5c80-36b0-5d97-9498-2f72b19a2239",
                "technician_id": "2c8d3073-36eb-5528-9287-12f86b2400be",
                "planned_start_time": "2026-10-30T09:00:00+05:30",
                "planned_end_time": "2026-10-30T10:00:00+05:30",
                "estimated_travel_minutes": 15,
                "assignment_status": "PLANNED",
                "assignment_reason": "Scheduled by engine",
            }
        }
    )

    job_id: uuid.UUID
    technician_id: uuid.UUID
    planned_start_time: datetime
    planned_end_time: datetime
    estimated_travel_minutes: int = Field(default=0, ge=0)
    assignment_status: AssignmentStatus = Field(default=AssignmentStatus.PLANNED)
    assignment_reason: str = Field(default="Scheduled by engine", max_length=1000)

    @model_validator(mode="after")
    def validate_planned_times(self) -> "ProposedAssignmentInput":
        ps = ensure_timezone_aware(self.planned_start_time)
        pe = ensure_timezone_aware(self.planned_end_time)
        if pe <= ps:
            raise ValueError("planned_end_time must be strictly after planned_start_time.")
        self.planned_start_time = ps
        self.planned_end_time = pe
        return self


class AssignmentResponse(BaseModel):
    """Response schema for persisted Assignment records."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    technician_id: uuid.UUID
    schedule_version_id: uuid.UUID
    planned_start_time: datetime
    planned_end_time: datetime
    estimated_travel_minutes: int
    assignment_status: str
    assignment_reason: str
    created_at: datetime

