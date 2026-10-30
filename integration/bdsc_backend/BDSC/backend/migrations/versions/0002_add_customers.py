"""Add external Customer (Client) entity table and link to Jobs.

Revision ID: 0002_add_customers
Revises: 0001_initial_schema
Create Date: 2026-10-30 20:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_add_customers"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("customer_code", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone_number", sa.String(length=32), nullable=False),
        sa.Column("alternate_phone_number", sa.String(length=32), nullable=True),
        sa.Column("customer_type", sa.String(length=32), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("service_address", sa.Text(), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("state", sa.String(length=120), nullable=False),
        sa.Column("postal_code", sa.String(length=32), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("latitude >= -90.0 AND latitude <= 90.0", name="ck_customer_latitude"),
        sa.CheckConstraint(
            "longitude >= -180.0 AND longitude <= 180.0", name="ck_customer_longitude"
        ),
        sa.CheckConstraint(
            "customer_type IN ('INDIVIDUAL', 'BUSINESS')",
            name="ck_customer_valid_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_code", name="uq_customers_customer_code"),
    )
    op.create_index("ix_customers_customer_code", "customers", ["customer_code"], unique=True)
    op.create_index("ix_customers_full_name", "customers", ["full_name"], unique=False)
    op.create_index("ix_customers_email", "customers", ["email"], unique=False)
    op.create_index("ix_customers_phone_number", "customers", ["phone_number"], unique=False)
    op.create_index("ix_customers_customer_type", "customers", ["customer_type"], unique=False)
    op.create_index("ix_customers_city", "customers", ["city"], unique=False)
    op.create_index("ix_customers_state", "customers", ["state"], unique=False)
    op.create_index("ix_customers_postal_code", "customers", ["postal_code"], unique=False)
    op.create_index("ix_customers_is_active", "customers", ["is_active"], unique=False)
    op.create_index(
        "ix_customers_active_type_city",
        "customers",
        ["is_active", "customer_type", "city"],
        unique=False,
    )

    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("customer_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.create_index("ix_jobs_customer_id", ["customer_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_jobs_customer_id_customers",
            "customers",
            ["customer_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_constraint("fk_jobs_customer_id_customers", type_="foreignkey")
        batch_op.drop_index("ix_jobs_customer_id")
        batch_op.drop_column("customer_id")

    op.drop_table("customers")

