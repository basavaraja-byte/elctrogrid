"""Pydantic v2 schemas for Technician management and time-aware availability."""

from datetime import datetime, time
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import AvailabilityStatus
from app.utils.validators import compute_shift_duration_minutes, ensure_timezone_aware

TECHNICIAN_EXAMPLE = {
    "name": "Ramesh Gowda",
    "phone": "+91-9845011223",
    "skills": [
        "Residential wiring",
        "Circuit breaker repair",
        "Distribution board maintenance",
    ],
    "service_zones": ["BLR-SOUTH-JAYANAGAR", "BLR-SE-KORAMANGALA"],
    "latitude": 12.9250,
    "longitude": 77.5938,
    "shift_start": "08:00:00",
    "shift_end": "17:00:00",
    "is_active": True,
    "availability_status": "AVAILABLE",
    "unavailable_windows": [
        {
            "start": "2026-10-30T13:00:00+05:30",
            "end": "2026-10-30T13:30:00+05:30",
            "status": "ON_BREAK",
            "reason": "Scheduled lunch break",
        }
    ],
}


class UnavailableWindowSchema(BaseModel):
    """Time-bounded break or unavailable window for a technician."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start": "2026-10-30T13:00:00+05:30",
                "end": "2026-10-30T13:30:00+05:30",
                "status": "ON_BREAK",
                "reason": "Scheduled lunch break",
            }
        }
    )

    start: datetime
    end: datetime
    status: AvailabilityStatus = Field(default=AvailabilityStatus.ON_BREAK)
    reason: str = Field(default="Scheduled break", min_length=1, max_length=255)

    @model_validator(mode="after")
    def validate_window(self) -> "UnavailableWindowSchema":
        s = ensure_timezone_aware(self.start)
        e = ensure_timezone_aware(self.end)
        if e <= s:
            raise ValueError("Unavailable window end must be strictly after start.")
        if self.status not in (
            AvailabilityStatus.ON_BREAK,
            AvailabilityStatus.UNAVAILABLE,
            AvailabilityStatus.OFF_DUTY,
        ):
            raise ValueError(
                "Unavailable window status must be ON_BREAK, UNAVAILABLE, or OFF_DUTY."
            )
        self.start = s
        self.end = e
        return self


class TechnicianBase(BaseModel):
    """Shared properties for creating and updating an electrician technician."""

    name: str = Field(..., min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=32)
    skills: list[str] = Field(..., min_length=1)
    service_zones: list[str] = Field(..., min_length=1)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    shift_start: time
    shift_end: time
    is_active: bool = Field(default=True)
    availability_status: AvailabilityStatus = Field(default=AvailabilityStatus.AVAILABLE)
    unavailable_windows: list[UnavailableWindowSchema] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_trimmed_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Technician name cannot be blank or whitespace only.")
        return trimmed

    @field_validator("skills")
    @classmethod
    def validate_skills_non_empty(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v if s and s.strip()]
        if not cleaned:
            raise ValueError("Technician must have at least one valid electrical skill.")
        return list(dict.fromkeys(cleaned))

    @field_validator("service_zones")
    @classmethod
    def validate_service_zones_non_empty(cls, v: list[str]) -> list[str]:
        cleaned = [z.strip() for z in v if z and z.strip()]
        if not cleaned:
            raise ValueError("Technician must have at least one valid service zone.")
        return list(dict.fromkeys(cleaned))

    @model_validator(mode="after")
    def validate_shift_hours(self) -> "TechnicianBase":
        compute_shift_duration_minutes(self.shift_start, self.shift_end)
        return self


class TechnicianCreate(TechnicianBase):
    """Request schema for POST /api/v1/technicians."""

    model_config = ConfigDict(json_schema_extra={"example": TECHNICIAN_EXAMPLE})


class TechnicianUpdate(TechnicianBase):
    """Request schema for PUT /api/v1/technicians/{technician_id}."""

    model_config = ConfigDict(json_schema_extra={"example": TECHNICIAN_EXAMPLE})


class TechnicianAvailabilityPatch(BaseModel):
    """Request schema for PATCH /api/v1/technicians/{technician_id}/availability."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "availability_status": "ON_BREAK",
                "is_active": True,
                "unavailable_window": {
                    "start": "2026-10-30T13:00:00+05:30",
                    "end": "2026-10-30T13:30:00+05:30",
                    "status": "ON_BREAK",
                    "reason": "Scheduled lunch break",
                },
                "clear_unavailable_windows": False,
                "reason": "Technician started scheduled break",
            }
        }
    )

    availability_status: AvailabilityStatus
    is_active: bool | None = None
    unavailable_window: UnavailableWindowSchema | None = None
    clear_unavailable_windows: bool = False
    reason: str = Field(default="Availability updated via API", max_length=500)


class TechnicianResponse(BaseModel):
    """Response schema for Technician records."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    phone: str | None = None
    skills: list[str]
    service_zones: list[str]
    latitude: float
    longitude: float
    shift_start: time
    shift_end: time
    is_active: bool
    availability_status: AvailabilityStatus
    unavailable_windows: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TechnicianWindowAvailabilityResponse(BaseModel):
    """Response schema for time-aware technician availability check."""

    technician_id: uuid.UUID
    technician_name: str
    window_start: datetime
    window_end: datetime
    is_available: bool
    effective_status: AvailabilityStatus
    blocking_reason: str | None = None
