"""SchedulingRun SQLAlchemy 2.0 model."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ExecutionStatus, SchedulingRunType, SchedulingStrategy

if TYPE_CHECKING:
    from app.models.schedule import ScheduleVersion

JSONVariant = JSON().with_variant(JSONB, "postgresql")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SchedulingRun(Base):
    """Canonical Scheduling Run execution history entity."""

    __tablename__ = "scheduling_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    schedule_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("schedule_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )
    run_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SchedulingRunType.INITIAL.value,
        index=True,
    )
    strategy: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=SchedulingStrategy.BALANCED.value,
    )
    execution_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ExecutionStatus.COMPLETED.value,
        index=True,
    )
    total_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assigned_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unassigned_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_travel_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_late_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unassigned_details: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONVariant,
        nullable=False,
        default=list,
    )
    sla_risks: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONVariant,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    # Relationships
    schedule_version: Mapped["ScheduleVersion | None"] = relationship(
        "ScheduleVersion",
        back_populates="scheduling_runs",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_scheduling_run_idempotency_key"),
        Index("ix_scheduling_runs_type_status", "run_type", "execution_status"),
    )

