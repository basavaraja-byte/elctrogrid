"""Customer (Client) SQLAlchemy 2.0 model (Module 1)."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import CustomerType
from app.utils.validators import generate_customer_code

if TYPE_CHECKING:
    from app.models.job import Job


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Customer(Base):
    """Canonical Customer (Client) entity representing an external individual or business requesting electrical services."""

    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    customer_code: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=generate_customer_code,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    phone_number: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )
    alternate_phone_number: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    customer_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=CustomerType.INDIVIDUAL.value,
        index=True,
    )
    company_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    service_address: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Bengaluru",
        index=True,
    )
    state: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Karnataka",
    )
    postal_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
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
    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="customer",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("customer_code", name="uq_customer_customer_code"),
        CheckConstraint("latitude >= -90.0 AND latitude <= 90.0", name="ck_customer_latitude"),
        CheckConstraint(
            "longitude >= -180.0 AND longitude <= 180.0", name="ck_customer_longitude"
        ),
        Index("ix_customers_type_active", "customer_type", "is_active"),
    )

