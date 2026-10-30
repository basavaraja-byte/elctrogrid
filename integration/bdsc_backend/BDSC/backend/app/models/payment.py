"""SQLAlchemy 2.0 models for Payments, Damaged Components, and Invoices."""

from datetime import datetime, timezone
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.job import Job


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Payment(Base):
    """Canonical Payment record for field service jobs."""

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    payment_reference: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    technician_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    work_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    work_completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    base_amount_paise: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50000,
    )
    additional_blocks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    additional_amount_paise: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    labour_total_paise: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50000,
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="INR",
    )
    payment_method: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="CASH",
    )
    payment_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
        index=True,
    )
    razorpay_order_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    razorpay_payment_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    confirmed_by: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
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
    damaged_components: Mapped[list["DamagedComponent"]] = relationship(
        "DamagedComponent",
        back_populates="payment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice",
        back_populates="payment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class DamagedComponent(Base):
    """Component or part identified as damaged or needing replacement."""

    __tablename__ = "damaged_components"

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
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    component_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    damage_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    photo_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    price_status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="Price to be confirmed",
    )
    estimated_part_amount_paise: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    remarks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    reported_by: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    # Relationships
    payment: Mapped["Payment | None"] = relationship(
        "Payment",
        back_populates="damaged_components",
        lazy="selectin",
    )


class Invoice(Base):
    """Official Invoice / Receipt record generated upon confirmed payment."""

    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    invoice_number: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    technician_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    customer_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    technician_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    service_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    invoice_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    labour_amount_paise: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    additional_amount_paise: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    parts_amount_paise: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    total_paid_paise: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    payment_method: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    payment_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PAID",
    )
    pdf_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    # Relationships
    payment: Mapped["Payment"] = relationship(
        "Payment",
        back_populates="invoices",
        lazy="selectin",
    )

