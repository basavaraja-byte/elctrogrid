"""ScheduleVersion SQLAlchemy 2.0 model."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ScheduleVersionStatus

if TYPE_CHECKING:
    from app.models.assignment import Assignment
    from app.models.audit_log import AuditLog
    from app.models.scheduling_run import SchedulingRun


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScheduleVersion(Base):
    """Canonical Schedule Version entity preserving full schedule history."""

    __tablename__ = "schedule_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ScheduleVersionStatus.DRAFT.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
    created_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="system",
    )
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("schedule_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    decision_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    parent_version: Mapped["ScheduleVersion | None"] = relationship(
        "ScheduleVersion",
        remote_side="ScheduleVersion.id",
        lazy="selectin",
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        "Assignment",
        back_populates="schedule_version",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    scheduling_runs: Mapped[list["SchedulingRun"]] = relationship(
        "SchedulingRun",
        back_populates="schedule_version",
        lazy="selectin",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="schedule_version",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("version_number", name="uq_schedule_version_number"),
        Index("ix_schedule_versions_status_version", "status", "version_number"),
    )

