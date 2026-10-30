"""Assignment SQLAlchemy 2.0 model."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import AssignmentStatus

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.schedule import ScheduleVersion
    from app.models.technician import Technician


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Assignment(Base):
    """Canonical Technician-to-Job Assignment entity bound to a ScheduleVersion."""

    __tablename__ = "assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    technician_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("technicians.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    schedule_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("schedule_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    planned_start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    planned_end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    estimated_travel_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    assignment_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AssignmentStatus.PLANNED.value,
    )
    assignment_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    # Relationships (no duplicated technician or job fields stored on Assignment)
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="assignments",
        lazy="selectin",
    )
    technician: Mapped["Technician"] = relationship(
        "Technician",
        back_populates="assignments",
        lazy="selectin",
    )
    schedule_version: Mapped["ScheduleVersion"] = relationship(
        "ScheduleVersion",
        back_populates="assignments",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "planned_end_time > planned_start_time",
            name="ck_assignment_valid_planned_window",
        ),
        CheckConstraint(
            "estimated_travel_minutes >= 0",
            name="ck_assignment_non_negative_travel",
        ),
        UniqueConstraint(
            "schedule_version_id",
            "job_id",
            name="uq_assignment_schedule_job",
        ),
        Index(
            "ix_assignment_version_tech_start",
            "schedule_version_id",
            "technician_id",
            "planned_start_time",
        ),
    )

