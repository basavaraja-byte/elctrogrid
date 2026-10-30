"""AuditLog SQLAlchemy 2.0 model."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.schedule import ScheduleVersion

JSONVariant = JSON().with_variant(JSONB, "postgresql")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    """Canonical immutable Audit Log entry for tracking entity and schedule changes."""

    __tablename__ = "audit_logs"

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
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant, nullable=True)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        index=True,
    )

    # Relationships
    schedule_version: Mapped["ScheduleVersion | None"] = relationship(
        "ScheduleVersion",
        back_populates="audit_logs",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_audit_logs_entity_lookup", "entity_type", "entity_id", "created_at"),
    )

