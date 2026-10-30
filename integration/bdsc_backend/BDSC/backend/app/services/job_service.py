"""Electrical Service Job management service with state machine and immutability guards."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.models.customer import Customer
from app.models.enums import JobPriority, JobStatus
from app.models.job import Job
from app.models.technician import Technician
from app.schemas.job import JobCreate, JobStatusPatch, JobUpdate
from app.services.audit_service import AuditService
from app.utils.validators import (
    ensure_timezone_aware,
    validate_coordinates,
    validate_job_status_transition,
)


class JobService:
    """Service layer for Electrical Service Job CRUD, state transitions, and immutability checks."""

    @staticmethod
    def _validate_assigned_technician(
        db: Session,
        technician_id: uuid.UUID | None,
        required_skills: list[str],
        service_zone: str,
    ) -> None:
        if technician_id is None:
            return
        tech = db.get(Technician, technician_id)
        if not tech:
            raise NotFoundException("Technician", technician_id)
        if not tech.is_active:
            raise ValidationException(
                code="INACTIVE_TECHNICIAN",
                message=f"Inactive technician '{tech.name}' ({tech.id}) cannot receive assignments.",
                status_code=400,
                details=[{"technician_id": str(tech.id), "is_active": False}],
            )
        missing_skills = set(required_skills) - set(tech.skills or [])
        if missing_skills:
            raise ValidationException(
                code="HARD_CONSTRAINT_VIOLATION",
                message=f"Technician '{tech.name}' lacks required skills: {sorted(missing_skills)}",
                status_code=400,
                details=[{"missing_skills": sorted(missing_skills)}],
            )
        if service_zone not in (tech.service_zones or []):
            raise ValidationException(
                code="HARD_CONSTRAINT_VIOLATION",
                message=f"Technician '{tech.name}' does not serve zone '{service_zone}'.",
                status_code=400,
                details=[{"service_zone": service_zone, "technician_zones": tech.service_zones}],
            )

    @classmethod
    def create_job(cls, db: Session, payload: JobCreate) -> Job:
        """Create and persist a new electrical service job."""
        validate_coordinates(payload.latitude, payload.longitude)
        resolved_customer_name = payload.customer_name
        resolved_customer_contact = payload.customer_contact

        if payload.customer_id is not None:
            customer = db.get(Customer, payload.customer_id)
            if not customer:
                raise NotFoundException("Customer", payload.customer_id)
            if not resolved_customer_name:
                resolved_customer_name = customer.full_name
            if not resolved_customer_contact:
                resolved_customer_contact = customer.phone_number

        if not resolved_customer_name:
            raise ValidationException(
                code="VALIDATION_ERROR",
                message="customer_name is required when customer_id is not provided.",
                status_code=422,
                details=[{"field": "customer_name", "issue": "Field required"}],
            )

        cls._validate_assigned_technician(
            db,
            payload.assigned_technician_id,
            payload.required_skills,
            payload.service_zone,
        )

        initial_status = payload.status
        if payload.assigned_technician_id and initial_status == JobStatus.PENDING:
            initial_status = JobStatus.ASSIGNED

        job = Job(
            customer_id=payload.customer_id,
            customer_name=resolved_customer_name,
            customer_contact=resolved_customer_contact,
            job_type=payload.job_type,
            description=payload.description,
            required_skills=payload.required_skills,
            priority=payload.priority.value,
            status=initial_status.value,
            latitude=payload.latitude,
            longitude=payload.longitude,
            service_zone=payload.service_zone,
            estimated_duration_minutes=payload.estimated_duration_minutes,
            appointment_window_start=ensure_timezone_aware(payload.appointment_window_start),
            appointment_window_end=ensure_timezone_aware(payload.appointment_window_end),
            sla_deadline=ensure_timezone_aware(payload.sla_deadline),
            assigned_technician_id=payload.assigned_technician_id,
        )
        db.add(job)
        db.flush()

        AuditService.log_event(
            db,
            entity_type="JOB",
            entity_id=job.id,
            action="CREATE",
            new_value={
                "customer_name": job.customer_name,
                "job_type": job.job_type,
                "priority": job.priority,
                "status": job.status,
                "service_zone": job.service_zone,
                "assigned_technician_id": job.assigned_technician_id,
            },
            reason="Created electrical service job",
        )
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def get_job_by_id(db: Session, job_id: uuid.UUID) -> Job:
        """Retrieve a job by UUID or raise 404 NotFoundException."""
        job = db.get(Job, job_id)
        if not job:
            raise NotFoundException("Job", job_id)
        return job

    @staticmethod
    def list_jobs(
        db: Session,
        *,
        customer_id: uuid.UUID | None = None,
        status: JobStatus | None = None,
        priority: JobPriority | None = None,
        service_zone: str | None = None,
        job_type: str | None = None,
        required_skill: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Job]:
        """List jobs with optional filters."""
        stmt = select(Job).order_by(Job.appointment_window_start.asc(), Job.created_at.asc())

        if customer_id is not None:
            stmt = stmt.where(Job.customer_id == customer_id)
        if status is not None:
            stmt = stmt.where(Job.status == status.value)
        if priority is not None:
            stmt = stmt.where(Job.priority == priority.value)
        if service_zone is not None:
            stmt = stmt.where(Job.service_zone == service_zone.strip())
        if job_type is not None:
            stmt = stmt.where(Job.job_type == job_type.strip())

        jobs = list(db.scalars(stmt).all())

        if required_skill:
            skill_lower = required_skill.strip().lower()
            jobs = [
                j
                for j in jobs
                if any(s.lower() == skill_lower for s in (j.required_skills or []))
            ]

        return jobs[skip : skip + limit]

    @classmethod
    def update_job(cls, db: Session, job_id: uuid.UUID, payload: JobUpdate) -> Job:
        """Full update of a job, enforcing immutability for COMPLETED and IN_PROGRESS jobs."""
        job = cls.get_job_by_id(db, job_id)

        if job.status in (JobStatus.COMPLETED.value, JobStatus.IN_PROGRESS.value):
            raise ConflictException(
                code="IMMUTABLE_JOB_VIOLATION",
                message=(
                    f"Job '{job.id}' has status '{job.status}' and is protected from "
                    "reassignment or window/skill modification."
                ),
                details=[{"job_id": str(job.id), "status": job.status}],
            )

        validate_coordinates(payload.latitude, payload.longitude)
        resolved_customer_name = payload.customer_name
        resolved_customer_contact = payload.customer_contact

        if payload.customer_id is not None:
            customer = db.get(Customer, payload.customer_id)
            if not customer:
                raise NotFoundException("Customer", payload.customer_id)
            if not resolved_customer_name:
                resolved_customer_name = customer.full_name
            if not resolved_customer_contact:
                resolved_customer_contact = customer.phone_number

        if not resolved_customer_name:
            raise ValidationException(
                code="VALIDATION_ERROR",
                message="customer_name is required when customer_id is not provided.",
                status_code=422,
                details=[{"field": "customer_name", "issue": "Field required"}],
            )

        cls._validate_assigned_technician(
            db,
            payload.assigned_technician_id,
            payload.required_skills,
            payload.service_zone,
        )

        old_snapshot = {
            "customer_id": job.customer_id,
            "customer_name": job.customer_name,
            "job_type": job.job_type,
            "required_skills": job.required_skills,
            "priority": job.priority,
            "status": job.status,
            "service_zone": job.service_zone,
            "estimated_duration_minutes": job.estimated_duration_minutes,
            "appointment_window_start": job.appointment_window_start,
            "appointment_window_end": job.appointment_window_end,
            "sla_deadline": job.sla_deadline,
            "assigned_technician_id": job.assigned_technician_id,
        }

        job.customer_id = payload.customer_id
        job.customer_name = resolved_customer_name
        job.customer_contact = resolved_customer_contact
        job.job_type = payload.job_type
        job.description = payload.description
        job.required_skills = payload.required_skills
        job.priority = payload.priority.value
        job.latitude = payload.latitude
        job.longitude = payload.longitude
        job.service_zone = payload.service_zone
        job.estimated_duration_minutes = payload.estimated_duration_minutes
        job.appointment_window_start = ensure_timezone_aware(payload.appointment_window_start)
        job.appointment_window_end = ensure_timezone_aware(payload.appointment_window_end)
        job.sla_deadline = ensure_timezone_aware(payload.sla_deadline)
        job.assigned_technician_id = payload.assigned_technician_id

        if payload.assigned_technician_id and job.status in (
            JobStatus.PENDING.value,
            JobStatus.UNASSIGNED.value,
        ):
            job.status = JobStatus.ASSIGNED.value
        elif payload.assigned_technician_id is None and job.status == JobStatus.ASSIGNED.value:
            job.status = JobStatus.UNASSIGNED.value

        new_snapshot = {
            "customer_name": job.customer_name,
            "job_type": job.job_type,
            "required_skills": job.required_skills,
            "priority": job.priority,
            "status": job.status,
            "service_zone": job.service_zone,
            "estimated_duration_minutes": job.estimated_duration_minutes,
            "appointment_window_start": job.appointment_window_start,
            "appointment_window_end": job.appointment_window_end,
            "sla_deadline": job.sla_deadline,
            "assigned_technician_id": job.assigned_technician_id,
        }

        AuditService.log_event(
            db,
            entity_type="JOB",
            entity_id=job.id,
            action="UPDATE",
            old_value=old_snapshot,
            new_value=new_snapshot,
            reason="Updated job details",
        )
        db.commit()
        db.refresh(job)
        return job

    @classmethod
    def patch_job_status(
        cls,
        db: Session,
        job_id: uuid.UUID,
        payload: JobStatusPatch,
    ) -> Job:
        """Transition job status enforcing the canonical state machine."""
        job = cls.get_job_by_id(db, job_id)
        validate_job_status_transition(job.status, payload.status.value)

        old_snapshot = {
            "status": job.status,
            "assigned_technician_id": job.assigned_technician_id,
            "actual_start_time": job.actual_start_time,
            "actual_completion_time": job.actual_completion_time,
        }

        target_status = payload.status
        now_utc = datetime.now(timezone.utc)

        if target_status == JobStatus.ASSIGNED:
            tech_id = payload.assigned_technician_id or job.assigned_technician_id
            if tech_id is None:
                raise ValidationException(
                    code="VALIDATION_ERROR",
                    message="Transitioning job to ASSIGNED requires an assigned_technician_id.",
                    status_code=400,
                )
            cls._validate_assigned_technician(
                db, tech_id, job.required_skills, job.service_zone
            )
            job.assigned_technician_id = tech_id

        elif target_status == JobStatus.IN_PROGRESS:
            if not job.assigned_technician_id and not payload.assigned_technician_id:
                raise ValidationException(
                    code="VALIDATION_ERROR",
                    message="Cannot start a job (IN_PROGRESS) without an assigned technician.",
                    status_code=400,
                )
            if payload.assigned_technician_id:
                cls._validate_assigned_technician(
                    db,
                    payload.assigned_technician_id,
                    job.required_skills,
                    job.service_zone,
                )
                job.assigned_technician_id = payload.assigned_technician_id
            job.actual_start_time = (
                ensure_timezone_aware(payload.actual_start_time)
                if payload.actual_start_time
                else now_utc
            )

        elif target_status == JobStatus.COMPLETED:
            job.actual_completion_time = (
                ensure_timezone_aware(payload.actual_completion_time)
                if payload.actual_completion_time
                else now_utc
            )
            if job.actual_start_time and job.actual_completion_time <= ensure_timezone_aware(
                job.actual_start_time
            ):
                raise ValidationException(
                    code="VALIDATION_ERROR",
                    message="actual_completion_time must be after actual_start_time.",
                    status_code=400,
                )

        elif target_status in (JobStatus.UNASSIGNED, JobStatus.PENDING):
            job.assigned_technician_id = None

        job.status = target_status.value

        new_snapshot = {
            "status": job.status,
            "assigned_technician_id": job.assigned_technician_id,
            "actual_start_time": job.actual_start_time,
            "actual_completion_time": job.actual_completion_time,
        }

        AuditService.log_event(
            db,
            entity_type="JOB",
            entity_id=job.id,
            action="STATUS_CHANGE",
            old_value=old_snapshot,
            new_value=new_snapshot,
            reason=payload.reason,
        )
        db.commit()
        db.refresh(job)
        return job

    @classmethod
    def delete_job(cls, db: Session, job_id: uuid.UUID) -> dict[str, str]:
        """Delete a job unless it is currently IN_PROGRESS or COMPLETED."""
        job = cls.get_job_by_id(db, job_id)
        if job.status in (JobStatus.IN_PROGRESS.value, JobStatus.COMPLETED.value):
            raise ConflictException(
                code="IMMUTABLE_JOB_VIOLATION",
                message=f"Cannot delete job '{job.id}' while its status is '{job.status}'.",
                details=[{"job_id": str(job.id), "status": job.status}],
            )

        AuditService.log_event(
            db,
            entity_type="JOB",
            entity_id=job.id,
            action="DELETE",
            old_value={
                "customer_name": job.customer_name,
                "status": job.status,
                "service_zone": job.service_zone,
            },
            reason="Job deleted via API",
        )
        db.delete(job)
        db.commit()
        return {"status": "deleted", "job_id": str(job_id)}

