"""Initial DISPATCHGRID canonical schema.

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-10-30 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONVariant = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    # 1. technicians
    op.create_table(
        "technicians",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("skills", JSONVariant, nullable=False),
        sa.Column("service_zones", JSONVariant, nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("shift_start", sa.Time(timezone=False), nullable=False),
        sa.Column("shift_end", sa.Time(timezone=False), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("availability_status", sa.String(length=32), nullable=False),
        sa.Column("unavailable_windows", JSONVariant, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("latitude >= -90.0 AND latitude <= 90.0", name="ck_technician_latitude"),
        sa.CheckConstraint(
            "longitude >= -180.0 AND longitude <= 180.0", name="ck_technician_longitude"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_technicians_name", "technicians", ["name"], unique=False)
    op.create_index("ix_technicians_is_active", "technicians", ["is_active"], unique=False)
    op.create_index(
        "ix_technicians_availability_status",
        "technicians",
        ["availability_status"],
        unique=False,
    )
    op.create_index(
        "ix_technicians_active_status",
        "technicians",
        ["is_active", "availability_status"],
        unique=False,
    )

    # 2. jobs
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("customer_name", sa.String(length=200), nullable=False),
        sa.Column("customer_contact", sa.String(length=64), nullable=True),
        sa.Column("job_type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("required_skills", JSONVariant, nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("service_zone", sa.String(length=100), nullable=False),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("appointment_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("appointment_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assigned_technician_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("actual_start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_completion_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "estimated_duration_minutes > 0",
            name="ck_job_positive_duration",
        ),
        sa.CheckConstraint(
            "appointment_window_end > appointment_window_start",
            name="ck_job_valid_appointment_window",
        ),
        sa.CheckConstraint("latitude >= -90.0 AND latitude <= 90.0", name="ck_job_latitude"),
        sa.CheckConstraint("longitude >= -180.0 AND longitude <= 180.0", name="ck_job_longitude"),
        sa.ForeignKeyConstraint(
            ["assigned_technician_id"],
            ["technicians.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_job_type", "jobs", ["job_type"], unique=False)
    op.create_index("ix_jobs_priority", "jobs", ["priority"], unique=False)
    op.create_index("ix_jobs_status", "jobs", ["status"], unique=False)
    op.create_index("ix_jobs_service_zone", "jobs", ["service_zone"], unique=False)
    op.create_index(
        "ix_jobs_appointment_window_start",
        "jobs",
        ["appointment_window_start"],
        unique=False,
    )
    op.create_index("ix_jobs_sla_deadline", "jobs", ["sla_deadline"], unique=False)
    op.create_index(
        "ix_jobs_assigned_technician_id",
        "jobs",
        ["assigned_technician_id"],
        unique=False,
    )
    op.create_index(
        "ix_jobs_status_priority_zone",
        "jobs",
        ["status", "priority", "service_zone"],
        unique=False,
    )

    # 3. schedule_versions
    op.create_table(
        "schedule_versions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("parent_version_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("approved_by", sa.String(length=100), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["schedule_versions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_number", name="uq_schedule_version_number"),
    )
    op.create_index(
        "ix_schedule_versions_version_number",
        "schedule_versions",
        ["version_number"],
        unique=False,
    )
    op.create_index("ix_schedule_versions_status", "schedule_versions", ["status"], unique=False)
    op.create_index(
        "ix_schedule_versions_parent_version_id",
        "schedule_versions",
        ["parent_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_schedule_versions_status_version",
        "schedule_versions",
        ["status", "version_number"],
        unique=False,
    )

    # 4. assignments
    op.create_table(
        "assignments",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("technician_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("schedule_version_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("planned_start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("planned_end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estimated_travel_minutes", sa.Integer(), nullable=False),
        sa.Column("assignment_status", sa.String(length=32), nullable=False),
        sa.Column("assignment_reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "planned_end_time > planned_start_time",
            name="ck_assignment_valid_planned_window",
        ),
        sa.CheckConstraint(
            "estimated_travel_minutes >= 0",
            name="ck_assignment_non_negative_travel",
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["schedule_version_id"],
            ["schedule_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["technician_id"], ["technicians.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "schedule_version_id",
            "job_id",
            name="uq_assignment_schedule_job",
        ),
    )
    op.create_index("ix_assignments_job_id", "assignments", ["job_id"], unique=False)
    op.create_index(
        "ix_assignments_technician_id",
        "assignments",
        ["technician_id"],
        unique=False,
    )
    op.create_index(
        "ix_assignments_schedule_version_id",
        "assignments",
        ["schedule_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_assignments_planned_start_time",
        "assignments",
        ["planned_start_time"],
        unique=False,
    )
    op.create_index(
        "ix_assignment_version_tech_start",
        "assignments",
        ["schedule_version_id", "technician_id", "planned_start_time"],
        unique=False,
    )

    # 5. scheduling_runs
    op.create_table(
        "scheduling_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("schedule_version_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=150), nullable=False),
        sa.Column("run_type", sa.String(length=32), nullable=False),
        sa.Column("strategy", sa.String(length=64), nullable=False),
        sa.Column("execution_status", sa.String(length=32), nullable=False),
        sa.Column("total_jobs", sa.Integer(), nullable=False),
        sa.Column("assigned_jobs", sa.Integer(), nullable=False),
        sa.Column("unassigned_jobs", sa.Integer(), nullable=False),
        sa.Column("total_travel_minutes", sa.Integer(), nullable=False),
        sa.Column("estimated_late_jobs", sa.Integer(), nullable=False),
        sa.Column("execution_time_ms", sa.Integer(), nullable=False),
        sa.Column("unassigned_details", JSONVariant, nullable=False),
        sa.Column("sla_risks", JSONVariant, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["schedule_version_id"],
            ["schedule_versions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_scheduling_run_idempotency_key"),
    )
    op.create_index(
        "ix_scheduling_runs_schedule_version_id",
        "scheduling_runs",
        ["schedule_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_scheduling_runs_idempotency_key",
        "scheduling_runs",
        ["idempotency_key"],
        unique=False,
    )
    op.create_index("ix_scheduling_runs_run_type", "scheduling_runs", ["run_type"], unique=False)
    op.create_index(
        "ix_scheduling_runs_execution_status",
        "scheduling_runs",
        ["execution_status"],
        unique=False,
    )
    op.create_index(
        "ix_scheduling_runs_type_status",
        "scheduling_runs",
        ["run_type", "execution_status"],
        unique=False,
    )

    # 6. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("schedule_version_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("old_value", JSONVariant, nullable=True),
        sa.Column("new_value", JSONVariant, nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["schedule_version_id"],
            ["schedule_versions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_logs_schedule_version_id",
        "audit_logs",
        ["schedule_version_id"],
        unique=False,
    )
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"], unique=False)
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"], unique=False)
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)
    op.create_index(
        "ix_audit_logs_entity_lookup",
        "audit_logs",
        ["entity_type", "entity_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("scheduling_runs")
    op.drop_table("assignments")
    op.drop_table("schedule_versions")
    op.drop_table("jobs")
    op.drop_table("technicians")

