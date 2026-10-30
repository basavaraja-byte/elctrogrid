"""Pydantic v2 schemas for Electrical Service Job CRUD and status transitions."""

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import JobPriority, JobStatus
from app.utils.validators import ensure_timezone_aware

JOB_CREATE_EXAMPLE = {
    "customer_id": None,
    "customer_name": "Kalyani Motors Workshop",
    "customer_contact": "+91-80-40921001",
    "job_type": "Distribution board maintenance",
    "description": "3-phase main distribution board thermal trip inspection",
    "required_skills": ["Distribution board maintenance", "Circuit breaker repair"],
    "priority": "HIGH",
    "latitude": 12.9716,
    "longitude": 77.5946,
    "service_zone": "BLR-CENTRAL-MG-ROAD",
    "estimated_duration_minutes": 60,
    "appointment_window_start": "2026-10-30T09:00:00+05:30",
    "appointment_window_end": "2026-10-30T13:00:00+05:30",
    "sla_deadline": "2026-10-30T14:00:00+05:30",
    "status": "PENDING",
    "assigned_technician_id": None,
}


class JobBase(BaseModel):
    """Shared properties for creating and updating an electrical service job."""

    customer_id: uuid.UUID | None = Field(default=None)
    customer_name: str | None = Field(default=None, min_length=2, max_length=200)
    customer_contact: str | None = Field(default=None, max_length=64)
    job_type: str = Field(..., min_length=2, max_length=100)
    description: str = Field(default="", max_length=2000)
    required_skills: list[str] = Field(..., min_length=1)
    priority: JobPriority = Field(default=JobPriority.MEDIUM)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    service_zone: str = Field(..., min_length=2, max_length=100)
    estimated_duration_minutes: int = Field(..., gt=0, le=1440)
    appointment_window_start: datetime
    appointment_window_end: datetime
    sla_deadline: datetime

    @field_validator("customer_id", mode="before")
    @classmethod
    def normalize_optional_customer_uuid(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("required_skills")
    @classmethod
    def validate_required_skills_non_empty(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v if s and s.strip()]
        if not cleaned:
            raise ValueError("Required skills cannot be empty.")
        return list(dict.fromkeys(cleaned))

    @field_validator("service_zone", "job_type")
    @classmethod
    def validate_trimmed_string(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Field cannot be blank or whitespace only.")
        return trimmed

    @field_validator("customer_name")
    @classmethod
    def validate_optional_customer_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("customer_name cannot be blank or whitespace only.")
        return trimmed

    @model_validator(mode="after")
    def validate_time_windows_and_sla(self) -> "JobBase":
        if self.customer_id is None and not self.customer_name:
            raise ValueError("customer_name is required when customer_id is not provided.")

        ws = ensure_timezone_aware(self.appointment_window_start)
        we = ensure_timezone_aware(self.appointment_window_end)
        sla = ensure_timezone_aware(self.sla_deadline)

        if we <= ws:
            raise ValueError("Appointment window end must be strictly after appointment window start.")

        window_minutes = (we - ws).total_seconds() / 60.0
        if window_minutes < self.estimated_duration_minutes:
            raise ValueError(
                f"Appointment window ({int(window_minutes)} mins) is shorter than estimated_duration_minutes ({self.estimated_duration_minutes} mins)."
            )

        if sla <= ws:
            raise ValueError("SLA deadline must be after appointment window start.")

        self.appointment_window_start = ws
        self.appointment_window_end = we
        self.sla_deadline = sla
        return self


class JobCreate(JobBase):
    """Request schema for POST /api/v1/jobs."""

    model_config = ConfigDict(json_schema_extra={"example": JOB_CREATE_EXAMPLE})

    status: JobStatus = Field(default=JobStatus.PENDING)
    assigned_technician_id: uuid.UUID | None = None

    @field_validator("assigned_technician_id", mode="before")
    @classmethod
    def normalize_optional_tech_uuid(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v


class JobUpdate(JobBase):
    """Request schema for PUT /api/v1/jobs/{job_id}."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {k: v for k, v in JOB_CREATE_EXAMPLE.items() if k != "status"}
        }
    )

    assigned_technician_id: uuid.UUID | None = None

    @field_validator("assigned_technician_id", mode="before")
    @classmethod
    def normalize_optional_tech_uuid(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v


class JobStatusPatch(BaseModel):
    """Request schema for PATCH /api/v1/jobs/{job_id}/status."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "IN_PROGRESS",
                "assigned_technician_id": None,
                "actual_start_time": "2026-10-30T09:30:00+05:30",
                "actual_completion_time": None,
                "reason": "Technician arrived on site and started electrical work",
            }
        }
    )

    status: JobStatus
    assigned_technician_id: uuid.UUID | None = None
    actual_start_time: datetime | None = None
    actual_completion_time: datetime | None = None
    reason: str = Field(default="Job status updated via API", max_length=500)

    @field_validator("assigned_technician_id", mode="before")
    @classmethod
    def normalize_optional_tech_uuid(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v


class JobResponse(BaseModel):
    """Response schema for Job records."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID | None = None
    customer_name: str
    customer_contact: str | None = None
    job_type: str
    description: str
    required_skills: list[str]
    priority: JobPriority
    status: JobStatus
    latitude: float
    longitude: float
    service_zone: str
    estimated_duration_minutes: int
    appointment_window_start: datetime
    appointment_window_end: datetime
    sla_deadline: datetime
    assigned_technician_id: uuid.UUID | None = None
    actual_start_time: datetime | None = None
    actual_completion_time: datetime | None = None
    created_at: datetime
    updated_at: datetime
