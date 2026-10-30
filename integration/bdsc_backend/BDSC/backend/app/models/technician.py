"""Technician SQLAlchemy 2.0 model."""

from datetime import datetime, time, timezone
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, Float, Index, String, Time, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import AvailabilityStatus

if TYPE_CHECKING:
    from app.models.assignment import Assignment
    from app.models.job import Job

JSONVariant = JSON().with_variant(JSONB, "postgresql")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Technician(Base):
    """Canonical Electrician Technician entity."""

    __tablename__ = "technicians"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    skills: Mapped[list[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    service_zones: Mapped[list[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    shift_start: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    shift_end: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    availability_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AvailabilityStatus.AVAILABLE.value,
        index=True,
    )
    # Time-aware unavailable / break windows: list of {"start": ISO, "end": ISO, "status": "ON_BREAK"|"UNAVAILABLE", "reason": str}
    unavailable_windows: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONVariant,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )

    # Relationships
    assigned_jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="assigned_technician",
        lazy="selectin",
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        "Assignment",
        back_populates="technician",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("latitude >= -90.0 AND latitude <= 90.0", name="ck_technician_latitude"),
        CheckConstraint(
            "longitude >= -180.0 AND longitude <= 180.0", name="ck_technician_longitude"
        ),
        Index("ix_technicians_active_status", "is_active", "availability_status"),
    )

