"""Common Pydantic v2 schemas for error responses, pagination, and audit logs."""

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetailItem(BaseModel):
    """Granular error detail item."""

    model_config = ConfigDict(extra="allow")

    field: str | None = None
    issue: str | None = None


class ErrorBody(BaseModel):
    """Inner error structure."""

    code: str
    message: str
    details: list[dict[str, Any]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Canonical API error envelope."""

    success: bool = False
    error: ErrorBody


class ConstraintViolationSchema(BaseModel):
    """Structured hard-constraint violation item returned by ConstraintValidator."""

    code: str
    severity: str = "HARD"
    job_id: uuid.UUID | None = None
    technician_id: uuid.UUID | None = None
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class AuditLogResponse(BaseModel):
    """Read schema for AuditLog entries."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    schedule_version_id: uuid.UUID | None = None
    entity_type: str
    entity_id: uuid.UUID
    action: str
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    reason: str
    created_at: datetime

