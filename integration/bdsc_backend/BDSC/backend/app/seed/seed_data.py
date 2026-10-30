"""Idempotent database seeder and reset CLI for DISPATCHGRID.

Usage:
    python -m app.seed.seed_data          # Idempotent upsert & reconciliation (exactly 20 techs & 100 jobs)
    python -m app.seed.seed_data --reset  # Clears existing tables and seeds fresh baseline data
"""

import argparse
from typing import Any

from sqlalchemy import delete, inspect, select, text, update
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal
from app.models.assignment import Assignment
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.enums import (
    ExecutionStatus,
    ScheduleVersionStatus,
    SchedulingRunType,
    SchedulingStrategy,
)
from app.models.job import Job
from app.models.schedule import ScheduleVersion
from app.models.scheduling_run import SchedulingRun
from app.models.technician import Technician
from app.seed.generate_dataset import _det_uuid, generate_synthetic_dataset


def _ensure_jobs_customer_id_column(db: Session) -> None:
    """Ensure existing SQLite/PostgreSQL jobs table has customer_id column if created prior to Module 1."""
    bind = db.get_bind()
    inspector = inspect(bind)
    if "jobs" in inspector.get_table_names():
        existing_cols = {col["name"] for col in inspector.get_columns("jobs")}
        if "customer_id" not in existing_cols:
            db.execute(
                text(
                    "ALTER TABLE jobs ADD COLUMN customer_id UUID REFERENCES customers(id) ON DELETE SET NULL"
                )
            )
            db.commit()


def seed_database(db: Session, *, reset: bool = False) -> dict[str, Any]:
    """Populate the database deterministically with customers, exactly 20 technicians, and 100 jobs."""
    Base.metadata.create_all(bind=db.get_bind())
    _ensure_jobs_customer_id_column(db)

    if reset:
        db.execute(delete(AuditLog))
        db.execute(delete(SchedulingRun))
        db.execute(delete(Assignment))
        db.execute(delete(ScheduleVersion))
        db.execute(delete(Job))
        db.execute(delete(Customer))
        db.execute(delete(Technician))
        db.commit()

    dataset = generate_synthetic_dataset()

    # Reconcile/remove any legacy seeded records beyond the canonical 20 technicians and 100 jobs
    # while preserving referential integrity (Instruction #7 & #9).
    legacy_tech_ids = [_det_uuid(f"tech-{i:02d}") for i in range(21, 30)]
    legacy_job_ids = [_det_uuid(f"job-{j:03d}") for j in range(101, 130)]

    db.execute(
        delete(Assignment).where(
            (Assignment.technician_id.in_(legacy_tech_ids))
            | (Assignment.job_id.in_(legacy_job_ids))
        )
    )
    db.execute(
        update(Job)
        .where(Job.assigned_technician_id.in_(legacy_tech_ids))
        .values(assigned_technician_id=None)
    )
    db.execute(delete(Job).where(Job.id.in_(legacy_job_ids)))
    db.execute(delete(Technician).where(Technician.id.in_(legacy_tech_ids)))
    db.flush()

    tech_created = 0
    tech_updated = 0

    for t_data in dataset["technicians"]:
        existing_tech = db.get(Technician, t_data["id"])
        if existing_tech is None:
            db.add(Technician(**t_data))
            tech_created += 1
        else:
            for k, v in t_data.items():
                setattr(existing_tech, k, v)
            tech_updated += 1

    db.flush()

    customer_created = 0
    customer_updated = 0
    for c_data in dataset.get("customers", []):
        existing_customer = db.get(Customer, c_data["id"])
        if existing_customer is None:
            db.add(Customer(**c_data))
            customer_created += 1
        else:
            for k, v in c_data.items():
                setattr(existing_customer, k, v)
            customer_updated += 1

    db.flush()

    job_created = 0
    job_updated = 0
    for j_data in dataset["jobs"]:
        existing_job = db.get(Job, j_data["id"])
        if existing_job is None:
            db.add(Job(**j_data))
            job_created += 1
        else:
            for k, v in j_data.items():
                setattr(existing_job, k, v)
            job_updated += 1

    db.flush()

    # Seed or synchronize initial ACTIVE schedule version v1 containing the 8 locked (COMPLETED + IN_PROGRESS) jobs
    v1_id = dataset["initial_schedule_version_id"]
    v1 = db.get(ScheduleVersion, v1_id)
    if v1 is None:
        v1 = db.scalar(
            select(ScheduleVersion).where(ScheduleVersion.version_number == 1)
        )
    if v1 is None:
        v1 = ScheduleVersion(
            id=v1_id,
            version_number=1,
            status=ScheduleVersionStatus.ACTIVE.value,
            created_by="seed_script",
            approved_by="system_bootstrap",
            decision_reason="Initial active baseline schedule with morning completed and in-progress dispatches",
        )
        db.add(v1)
        db.flush()

    for a_data in dataset["initial_locked_assignments"]:
        existing_assign = db.get(Assignment, a_data["id"])
        if existing_assign is None:
            db.add(
                Assignment(
                    id=a_data["id"],
                    job_id=a_data["job_id"],
                    technician_id=a_data["technician_id"],
                    schedule_version_id=v1.id,
                    planned_start_time=a_data["planned_start_time"],
                    planned_end_time=a_data["planned_end_time"],
                    estimated_travel_minutes=a_data["estimated_travel_minutes"],
                    assignment_status=a_data["assignment_status"],
                    assignment_reason=a_data["assignment_reason"],
                )
            )
        else:
            existing_assign.job_id = a_data["job_id"]
            existing_assign.technician_id = a_data["technician_id"]
            existing_assign.schedule_version_id = v1.id
            existing_assign.planned_start_time = a_data["planned_start_time"]
            existing_assign.planned_end_time = a_data["planned_end_time"]
            existing_assign.estimated_travel_minutes = a_data["estimated_travel_minutes"]
            existing_assign.assignment_status = a_data["assignment_status"]
            existing_assign.assignment_reason = a_data["assignment_reason"]

    run_id = dataset["initial_scheduling_run_id"]
    existing_run = db.get(SchedulingRun, run_id)
    if existing_run is None:
        db.add(
            SchedulingRun(
                id=run_id,
                schedule_version_id=v1.id,
                idempotency_key="seed-initial-baseline-v1",
                run_type=SchedulingRunType.INITIAL.value,
                strategy=SchedulingStrategy.BALANCED.value,
                execution_status=ExecutionStatus.COMPLETED.value,
                total_jobs=len(dataset["jobs"]),
                assigned_jobs=len(dataset["initial_locked_assignments"]),
                unassigned_jobs=len(dataset["jobs"])
                - len(dataset["initial_locked_assignments"]),
                total_travel_minutes=sum(
                    a["estimated_travel_minutes"]
                    for a in dataset["initial_locked_assignments"]
                ),
                estimated_late_jobs=0,
                execution_time_ms=12,
                unassigned_details=[],
                sla_risks=[],
            )
        )
    else:
        existing_run.total_jobs = len(dataset["jobs"])
        existing_run.assigned_jobs = len(dataset["initial_locked_assignments"])
        existing_run.unassigned_jobs = len(dataset["jobs"]) - len(
            dataset["initial_locked_assignments"]
        )

    db.commit()

    total_customers = len(list(db.scalars(select(Customer)).all()))
    total_techs = len(list(db.scalars(select(Technician)).all()))
    total_jobs = len(list(db.scalars(select(Job)).all()))

    return {
        "customers_created": customer_created,
        "customers_updated": customer_updated,
        "total_customers": total_customers,
        "technicians_created": tech_created,
        "technicians_updated": tech_updated,
        "total_technicians": total_techs,
        "jobs_created": job_created,
        "jobs_updated": job_updated,
        "total_jobs": total_jobs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed or reset the DISPATCHGRID synthetic electrician dataset."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Wipe existing tables before seeding deterministic dataset.",
    )
    args = parser.parse_args()

    with SessionLocal() as session:
        summary = seed_database(session, reset=args.reset)
        print("DISPATCHGRID Seed Complete:", summary)


if __name__ == "__main__":
    main()
