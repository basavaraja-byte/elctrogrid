"""Electrical Service Job SQLAlchemy 2.0 model."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import JobPriority, JobStatus

if TYPE_CHECKING:
    from app.models.assignment import Assignment
    from app.models.customer import Customer
    from app.models.technician import Technician

JSONVariant = JSON().with_variant(JSONB, "postgresql")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    """Canonical Electrical Service Job entity."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_contact: Mapped[str | None] = mapped_column(String(64), nullable=True)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    required_skills: Mapped[list[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    priority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=JobPriority.MEDIUM.value,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=JobStatus.PENDING.value,
        index=True,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    service_zone: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    appointment_window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    appointment_window_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    sla_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    assigned_technician_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("technicians.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actual_start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    actual_completion_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
    customer: Mapped["Customer | None"] = relationship(
        "Customer",
        back_populates="jobs",
        lazy="selectin",
    )
    assigned_technician: Mapped["Technician | None"] = relationship(
        "Technician",
        back_populates="assigned_jobs",
        lazy="selectin",
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        "Assignment",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "estimated_duration_minutes > 0",
            name="ck_job_positive_duration",
        ),
        CheckConstraint(
            "appointment_window_end > appointment_window_start",
            name="ck_job_valid_appointment_window",
        ),
        CheckConstraint("latitude >= -90.0 AND latitude <= 90.0", name="ck_job_latitude"),
        CheckConstraint("longitude >= -180.0 AND longitude <= 180.0", name="ck_job_longitude"),
        Index("ix_jobs_status_priority_zone", "status", "priority", "service_zone"),
    )

