"""Transactional schedule versioning, shared SchedulerEngineProtocol, human approval workflow, and persistence service."""

from datetime import datetime, timezone
import time as time_module
from typing import Protocol
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.models.assignment import Assignment
from app.models.audit_log import AuditLog
from app.models.enums import (
    AssignmentStatus,
    ExecutionStatus,
    JobPriority,
    JobStatus,
    ScheduleVersionStatus,
    SchedulingRunType,
    SchedulingStrategy,
)
from app.models.job import Job
from app.models.schedule import ScheduleVersion
from app.models.scheduling_run import SchedulingRun
from app.models.technician import Technician
from app.schemas.assignment import AssignmentResponse, ProposedAssignmentInput
from app.schemas.common import AuditLogResponse
from app.schemas.schedule import (
    CandidateRankingRequest,
    CandidateRankingResponse,
    ScheduleApproveRequest,
    ScheduleGenerateRequest,
    ScheduleGenerationResponse,
    ScheduleRejectRequest,
    ScheduleValidationRequest,
    ScheduleValidationResponse,
    ScheduleVersionResponse,
    SchedulingRunResponse,
    UnassignedJobReasonSchema,
)
from app.services.audit_service import AuditService
from app.services.constraint_validator import ConstraintValidator
from app.services.metrics_service import MetricsService
from app.services.scoring import CandidateScorer
from app.utils.validators import ensure_timezone_aware

PRIORITY_ORDER: dict[str, int] = {
    JobPriority.CRITICAL.value: 0,
    JobPriority.HIGH.value: 1,
    JobPriority.MEDIUM.value: 2,
    JobPriority.LOW.value: 3,
}


class SchedulerEngineProtocol(Protocol):
    """Shared integration protocol for plugging external Scheduling & Recovery engines into ScheduleService."""

    def solve(
        self,
        *,
        jobs: list[Job],
        technicians: list[Technician],
        parent_schedule: ScheduleVersion | None,
        request: ScheduleGenerateRequest,
    ) -> tuple[list[ProposedAssignmentInput], list[UnassignedJobReasonSchema]]:
        """Return (proposed_assignments, unassigned_reasons)."""
        ...


class BaselineFeasibleScheduler:
    """Default feasibility-preserving heuristic solver used when no external solver is registered or passed in payload."""

    def solve(
        self,
        *,
        jobs: list[Job],
        technicians: list[Technician],
        parent_schedule: ScheduleVersion | None,
        request: ScheduleGenerateRequest,
    ) -> tuple[list[ProposedAssignmentInput], list[UnassignedJobReasonSchema]]:
        """Construct a valid baseline schedule preserving COMPLETED and IN_PROGRESS jobs first."""
        proposed: list[ProposedAssignmentInput] = []
        unassigned_reasons: list[UnassignedJobReasonSchema] = []

        parent_by_job: dict[uuid.UUID, Assignment] = {}
        if parent_schedule is not None:
            parent_by_job = {
                a.job_id: a for a in (parent_schedule.assignments or [])
            }

        locked_job_ids: set[uuid.UUID] = set()
        jobs_by_id = {j.id: j for j in jobs}

        # Step 1: Lock all COMPLETED and IN_PROGRESS jobs from parent schedule untouched (Mandatory Addition #5)
        for jid, p_assign in parent_by_job.items():
            job = jobs_by_id.get(jid)
            if job and job.status in (JobStatus.COMPLETED.value, JobStatus.IN_PROGRESS.value):
                proposed.append(
                    ProposedAssignmentInput(
                        job_id=job.id,
                        technician_id=p_assign.technician_id,
                        planned_start_time=ensure_timezone_aware(p_assign.planned_start_time),
                        planned_end_time=ensure_timezone_aware(p_assign.planned_end_time),
                        estimated_travel_minutes=p_assign.estimated_travel_minutes,
                        assignment_status=(
                            AssignmentStatus.COMPLETED
                            if job.status == JobStatus.COMPLETED.value
                            else AssignmentStatus.IN_PROGRESS
                        ),
                        assignment_reason=f"Locked {job.status} assignment preserved from parent schedule",
                    )
                )
                locked_job_ids.add(job.id)

        # Step 2: Sort remaining eligible jobs by priority, SLA deadline, then appointment start
        remaining_jobs = [
            j
            for j in jobs
            if j.id not in locked_job_ids and j.status != JobStatus.CANCELLED.value
        ]
        remaining_jobs.sort(
            key=lambda j: (
                PRIORITY_ORDER.get(j.priority, 99),
                ensure_timezone_aware(j.sla_deadline),
                ensure_timezone_aware(j.appointment_window_start),
                str(j.id),
            )
        )

        # Step 3: Rank feasible technicians for each job using CandidateScorer
        for job in remaining_jobs:
            ranking = CandidateScorer.rank_candidates_for_job(
                job=job,
                technicians=technicians,
                existing_assignments=proposed,
                parent_assignments_by_job=parent_by_job,
                strategy=request.strategy,
            )
            if ranking.feasible_candidates:
                best = ranking.feasible_candidates[0]
                proposed.append(
                    ProposedAssignmentInput(
                        job_id=job.id,
                        technician_id=best.technician_id,
                        planned_start_time=best.planned_start_time,
                        planned_end_time=best.planned_end_time,
                        estimated_travel_minutes=best.estimated_travel_minutes,
                        assignment_status=AssignmentStatus.PLANNED,
                        assignment_reason=best.explanation,
                    )
                )
            else:
                # Aggregate primary reason why no technician was feasible
                violation_codes: list[str] = []
                for inf in ranking.infeasible_candidates:
                    for v in inf.violations:
                        if v.code not in violation_codes:
                            violation_codes.append(v.code)
                primary_code = violation_codes[0] if violation_codes else "NO_FEASIBLE_TECHNICIAN"
                unassigned_reasons.append(
                    UnassignedJobReasonSchema(
                        job_id=job.id,
                        reason_code=primary_code,
                        explanation=(
                            f"No feasible technician for job '{job.id}' in zone '{job.service_zone}' "
                            f"(blocking constraints: {', '.join(violation_codes[:4]) or 'none'})."
                        ),
                    )
                )

        return proposed, unassigned_reasons


class ScheduleService:
    """Shared schedule persistence, constraint enforcement, human approval, and versioning service."""

    _registered_engine: SchedulerEngineProtocol = BaselineFeasibleScheduler()

    @classmethod
    def register_scheduler_engine(cls, engine: SchedulerEngineProtocol) -> None:
        """Allow the Scheduler/Recovery teammate module to register its custom solver implementation."""
        cls._registered_engine = engine

    @staticmethod
    def get_current_active_version(db: Session) -> ScheduleVersion | None:
        """Return the single currently ACTIVE ScheduleVersion, if any."""
        return db.scalar(
            select(ScheduleVersion)
            .where(ScheduleVersion.status == ScheduleVersionStatus.ACTIVE.value)
            .order_by(ScheduleVersion.version_number.desc())
        )

    @staticmethod
    def _next_version_number(db: Session) -> int:
        max_v = db.scalar(select(func.max(ScheduleVersion.version_number)))
        return (max_v or 0) + 1

    @classmethod
    def _sync_jobs_to_active_schedule(
        cls,
        db: Session,
        active_version: ScheduleVersion,
    ) -> None:
        """Synchronize non-immutable Job rows (`assigned_technician_id` and `status`) to match `active_version`."""
        all_jobs = list(db.scalars(select(Job)).all())
        assign_by_job: dict[uuid.UUID, Assignment] = {
            a.job_id: a for a in (active_version.assignments or [])
        }
        for job in all_jobs:
            if job.status in (
                JobStatus.COMPLETED.value,
                JobStatus.IN_PROGRESS.value,
                JobStatus.CANCELLED.value,
            ):
                continue
            matched = assign_by_job.get(job.id)
            if matched is not None:
                job.assigned_technician_id = matched.technician_id
                job.status = JobStatus.ASSIGNED.value
            else:
                job.assigned_technician_id = None
                job.status = JobStatus.UNASSIGNED.value

    @classmethod
    def build_schedule_response(
        cls,
        db: Session,
        version: ScheduleVersion,
        run: SchedulingRun | None = None,
    ) -> ScheduleGenerationResponse:
        """Construct the canonical ScheduleGenerationResponse from persisted rows."""
        if run is None and version.scheduling_runs:
            run = sorted(
                version.scheduling_runs,
                key=lambda r: ensure_timezone_aware(r.created_at),
                reverse=True,
            )[0]

        all_jobs = list(db.scalars(select(Job)).all())
        jobs_by_id = {j.id: j for j in all_jobs}

        assignments = sorted(
            list(version.assignments or []),
            key=lambda a: (ensure_timezone_aware(a.planned_start_time), str(a.id)),
        )
        assigned_job_ids = {a.job_id for a in assignments}

        unassigned_job_ids = [
            j.id
            for j in all_jobs
            if j.status != JobStatus.CANCELLED.value and j.id not in assigned_job_ids
        ]

        unassigned_reasons: list[UnassignedJobReasonSchema] = []
        if run and run.unassigned_details:
            for item in run.unassigned_details:
                unassigned_reasons.append(
                    UnassignedJobReasonSchema(
                        job_id=uuid.UUID(str(item["job_id"])),
                        reason_code=str(item.get("reason_code", "UNASSIGNED")),
                        explanation=str(item.get("explanation", "Job unassigned")),
                    )
                )
        else:
            for u_jid in unassigned_job_ids:
                unassigned_reasons.append(
                    UnassignedJobReasonSchema(
                        job_id=u_jid,
                        reason_code="UNASSIGNED",
                        explanation="Job is not assigned in this schedule version.",
                    )
                )

        sla_risks = MetricsService.compute_sla_risks(assignments, jobs_by_id)
        total_travel = sum(max(0, a.estimated_travel_minutes or 0) for a in assignments)

        audit_entries = list(
            db.scalars(
                select(AuditLog)
                .where(AuditLog.schedule_version_id == version.id)
                .order_by(AuditLog.created_at.asc())
            ).all()
        )

        return ScheduleGenerationResponse(
            schedule_version=ScheduleVersionResponse.model_validate(version),
            scheduling_run=SchedulingRunResponse.model_validate(run) if run else None,
            assignments=[AssignmentResponse.model_validate(a) for a in assignments],
            unassigned_jobs=unassigned_job_ids,
            unassigned_reasons=unassigned_reasons,
            total_travel_minutes=total_travel,
            assigned_job_count=len(assignments),
            unassigned_job_count=len(unassigned_job_ids),
            sla_risk_information=sla_risks,
            audit_logs=[AuditLogResponse.model_validate(al) for al in audit_entries],
        )

    @classmethod
    def generate_schedule(
        cls,
        db: Session,
        request: ScheduleGenerateRequest,
    ) -> ScheduleGenerationResponse:
        """Transactional schedule generation with idempotency, hard-constraint validation, and human approval enforcement."""
        start_perf = time_module.perf_counter()

        # 1. Idempotency check
        existing_run = db.scalar(
            select(SchedulingRun).where(
                SchedulingRun.idempotency_key == request.idempotency_key
            )
        )
        if existing_run is not None:
            raise ConflictException(
                code="DUPLICATE_IDEMPOTENCY_KEY",
                message=f"Scheduling run with idempotency_key '{request.idempotency_key}' already exists.",
                details=[
                    {
                        "idempotency_key": request.idempotency_key,
                        "existing_run_id": str(existing_run.id),
                        "schedule_version_id": (
                            str(existing_run.schedule_version_id)
                            if existing_run.schedule_version_id
                            else None
                        ),
                    }
                ],
            )

        # 2. Enforce Mandatory Addition #4: Recovery runs must generate a DRAFT proposal first
        if request.run_type == SchedulingRunType.RECOVERY and request.auto_activate:
            raise ValidationException(
                code="APPROVAL_REQUIRED",
                message=(
                    "Disruption RECOVERY runs must be saved as DRAFT proposals first and "
                    "cannot be auto-activated without explicit Operations Manager approval."
                ),
                status_code=400,
                details=[{"run_type": request.run_type.value, "auto_activate": True}],
            )

        active_version = cls.get_current_active_version(db)
        parent_version: ScheduleVersion | None = None
        if request.parent_version_id is not None:
            parent_version = db.get(ScheduleVersion, request.parent_version_id)
            if parent_version is None:
                raise NotFoundException("ScheduleVersion", request.parent_version_id)
        else:
            parent_version = active_version

        # Also block silent auto-activation if an ACTIVE schedule already exists and would be disrupted
        if request.auto_activate and active_version is not None:
            raise ValidationException(
                code="APPROVAL_REQUIRED",
                message=(
                    "An ACTIVE schedule already exists. New schedule versions must be created as "
                    "DRAFT proposals and activated via the human approval endpoint."
                ),
                status_code=400,
                details=[{"current_active_schedule_id": str(active_version.id)}],
            )

        try:
            # Load jobs and technicians
            all_jobs = list(db.scalars(select(Job)).all())
            jobs_by_id: dict[uuid.UUID, Job] = {j.id: j for j in all_jobs}

            if request.job_ids is not None:
                missing_ids = [jid for jid in request.job_ids if jid not in jobs_by_id]
                if missing_ids:
                    raise NotFoundException("Job", missing_ids[0])
                target_jobs = [jobs_by_id[jid] for jid in request.job_ids]
                # Ensure any COMPLETED/IN_PROGRESS jobs from parent schedule are also included
                if parent_version is not None:
                    for pa in parent_version.assignments or []:
                        p_job = jobs_by_id.get(pa.job_id)
                        if (
                            p_job
                            and p_job.status
                            in (JobStatus.COMPLETED.value, JobStatus.IN_PROGRESS.value)
                            and p_job.id not in {tj.id for tj in target_jobs}
                        ):
                            target_jobs.append(p_job)
            else:
                target_jobs = [
                    j for j in all_jobs if j.status != JobStatus.CANCELLED.value
                ]

            all_techs = list(db.scalars(select(Technician)).all())
            techs_by_id: dict[uuid.UUID, Technician] = {t.id: t for t in all_techs}

            # 3. Obtain proposed assignments & unassigned reasons
            if request.proposed_assignments is not None:
                proposed_assignments = request.proposed_assignments
                unassigned_reasons = request.unassigned_reasons or []
            else:
                proposed_assignments, unassigned_reasons = cls._registered_engine.solve(
                    jobs=target_jobs,
                    technicians=all_techs,
                    parent_schedule=parent_version,
                    request=request,
                )

            # 4. Run centralized ConstraintValidator (Mandatory Addition #1 & #5)
            violations = ConstraintValidator.validate_schedule_bundle(
                assignments=proposed_assignments,
                jobs_by_id=jobs_by_id,
                technicians_by_id=techs_by_id,
                parent_schedule=parent_version,
            )
            if violations:
                primary_codes = {v.code for v in violations}
                if "ASSIGNMENT_OVERLAP" in primary_codes:
                    err_code = "ASSIGNMENT_OVERLAP"
                    status_code = 409
                elif "IMMUTABLE_JOB_VIOLATION" in primary_codes:
                    err_code = "IMMUTABLE_JOB_VIOLATION"
                    status_code = 409
                elif "INACTIVE_TECHNICIAN" in primary_codes:
                    err_code = "INACTIVE_TECHNICIAN"
                    status_code = 400
                else:
                    err_code = "HARD_CONSTRAINT_VIOLATION"
                    status_code = 400

                raise ValidationException(
                    code=err_code,
                    message=(
                        f"Schedule generation rejected due to {len(violations)} hard-constraint "
                        f"violation(s): {violations[0].message}"
                    ),
                    status_code=status_code,
                    details=[v.model_dump(mode="json") for v in violations],
                )

            # 5. Persist ScheduleVersion, Assignments, SchedulingRun, and AuditLog atomically
            next_v_num = cls._next_version_number(db)
            initial_status = (
                ScheduleVersionStatus.ACTIVE.value
                if request.auto_activate and active_version is None
                else ScheduleVersionStatus.DRAFT.value
            )

            new_version = ScheduleVersion(
                version_number=next_v_num,
                status=initial_status,
                created_by=request.created_by,
                parent_version_id=parent_version.id if parent_version else None,
            )
            db.add(new_version)
            db.flush()

            persisted_assignments: list[Assignment] = []
            for prop in proposed_assignments:
                assign_row = Assignment(
                    job_id=prop.job_id,
                    technician_id=prop.technician_id,
                    schedule_version_id=new_version.id,
                    planned_start_time=ensure_timezone_aware(prop.planned_start_time),
                    planned_end_time=ensure_timezone_aware(prop.planned_end_time),
                    estimated_travel_minutes=prop.estimated_travel_minutes,
                    assignment_status=prop.assignment_status.value,
                    assignment_reason=prop.assignment_reason,
                )
                db.add(assign_row)
                persisted_assignments.append(assign_row)

            db.flush()
            new_version.assignments = persisted_assignments

            assigned_job_ids = {a.job_id for a in persisted_assignments}
            unassigned_job_ids = [
                j.id
                for j in target_jobs
                if j.status != JobStatus.CANCELLED.value and j.id not in assigned_job_ids
            ]

            # Ensure every unassigned job in scope has an UnassignedJobReasonSchema entry
            existing_reason_jids = {r.job_id for r in unassigned_reasons}
            for u_jid in unassigned_job_ids:
                if u_jid not in existing_reason_jids:
                    unassigned_reasons.append(
                        UnassignedJobReasonSchema(
                            job_id=u_jid,
                            reason_code="UNASSIGNED_IN_PROPOSAL",
                            explanation="Job was not assigned in the submitted schedule proposal.",
                        )
                    )

            sla_risks = MetricsService.compute_sla_risks(persisted_assignments, jobs_by_id)
            late_count = sum(1 for r in sla_risks if r.is_late)
            total_travel = sum(
                max(0, a.estimated_travel_minutes or 0) for a in persisted_assignments
            )
            elapsed_ms = max(1, int(round((time_module.perf_counter() - start_perf) * 1000)))

            run_row = SchedulingRun(
                schedule_version_id=new_version.id,
                idempotency_key=request.idempotency_key,
                run_type=request.run_type.value,
                strategy=request.strategy.value,
                execution_status=ExecutionStatus.COMPLETED.value,
                total_jobs=len(target_jobs),
                assigned_jobs=len(persisted_assignments),
                unassigned_jobs=len(unassigned_job_ids),
                total_travel_minutes=total_travel,
                estimated_late_jobs=late_count,
                execution_time_ms=elapsed_ms,
                unassigned_details=[r.model_dump(mode="json") for r in unassigned_reasons],
                sla_risks=[r.model_dump(mode="json") for r in sla_risks],
            )
            db.add(run_row)

            if initial_status == ScheduleVersionStatus.ACTIVE.value:
                cls._sync_jobs_to_active_schedule(db, new_version)

            AuditService.log_event(
                db,
                schedule_version_id=new_version.id,
                entity_type="SCHEDULE_VERSION",
                entity_id=new_version.id,
                action=f"GENERATE_{request.run_type.value}",
                old_value=(
                    {"parent_version_id": str(parent_version.id)}
                    if parent_version
                    else None
                ),
                new_value={
                    "version_number": new_version.version_number,
                    "status": new_version.status,
                    "run_type": request.run_type.value,
                    "assigned_jobs": len(persisted_assignments),
                    "unassigned_jobs": len(unassigned_job_ids),
                    "total_travel_minutes": total_travel,
                },
                reason=(
                    f"Generated {request.run_type.value} schedule v{new_version.version_number} "
                    f"({new_version.status}) via strategy {request.strategy.value}"
                ),
            )

            db.commit()
            db.refresh(new_version)
            db.refresh(run_row)
            return cls.build_schedule_response(db, new_version, run_row)

        except Exception:
            db.rollback()
            raise

    @classmethod
    def approve_schedule(
        cls,
        db: Session,
        schedule_id: uuid.UUID,
        payload: ScheduleApproveRequest,
    ) -> ScheduleGenerationResponse:
        """Human approval by Operations Manager: re-validates constraints, supersedes old ACTIVE, and activates proposal."""
        version = db.get(ScheduleVersion, schedule_id)
        if not version:
            raise NotFoundException("ScheduleVersion", schedule_id)

        if version.status == ScheduleVersionStatus.ACTIVE.value:
            return cls.build_schedule_response(db, version)

        if version.status in (
            ScheduleVersionStatus.REJECTED.value,
            ScheduleVersionStatus.SUPERSEDED.value,
        ):
            raise ConflictException(
                code="INVALID_SCHEDULE_STATE",
                message=f"Cannot approve schedule version '{schedule_id}' in status '{version.status}'.",
                details=[{"schedule_id": str(schedule_id), "status": version.status}],
            )

        current_active = cls.get_current_active_version(db)
        all_jobs = list(db.scalars(select(Job)).all())
        jobs_by_id = {j.id: j for j in all_jobs}
        all_techs = list(db.scalars(select(Technician)).all())
        techs_by_id = {t.id: t for t in all_techs}

        # Re-validate all hard constraints and recovery protection against current_active before activation
        reference_parent = current_active or (
            db.get(ScheduleVersion, version.parent_version_id)
            if version.parent_version_id
            else None
        )
        violations = ConstraintValidator.validate_schedule_bundle(
            assignments=list(version.assignments or []),
            jobs_by_id=jobs_by_id,
            technicians_by_id=techs_by_id,
            parent_schedule=reference_parent,
        )
        if violations:
            raise ValidationException(
                code="HARD_CONSTRAINT_VIOLATION",
                message=(
                    f"Cannot approve schedule '{schedule_id}': {len(violations)} hard-constraint "
                    f"violation(s) detected ({violations[0].message})."
                ),
                status_code=409,
                details=[v.model_dump(mode="json") for v in violations],
            )

        try:
            old_active_id: str | None = None
            if current_active is not None and current_active.id != version.id:
                old_active_id = str(current_active.id)
                current_active.status = ScheduleVersionStatus.SUPERSEDED.value
                AuditService.log_event(
                    db,
                    schedule_version_id=current_active.id,
                    entity_type="SCHEDULE_VERSION",
                    entity_id=current_active.id,
                    action="SUPERSEDED",
                    old_value={"status": ScheduleVersionStatus.ACTIVE.value},
                    new_value={
                        "status": ScheduleVersionStatus.SUPERSEDED.value,
                        "superseded_by_version_id": str(version.id),
                    },
                    reason=f"Superseded by approved schedule version v{version.version_number}",
                )

            prev_status = version.status
            version.status = ScheduleVersionStatus.ACTIVE.value
            version.approved_by = payload.approved_by.strip()
            version.approved_at = datetime.now(timezone.utc)
            version.decision_reason = payload.reason.strip()

            cls._sync_jobs_to_active_schedule(db, version)

            AuditService.log_event(
                db,
                schedule_version_id=version.id,
                entity_type="SCHEDULE_VERSION",
                entity_id=version.id,
                action="APPROVE_AND_ACTIVATE",
                old_value={
                    "status": prev_status,
                    "previous_active_schedule_id": old_active_id,
                },
                new_value={
                    "status": ScheduleVersionStatus.ACTIVE.value,
                    "approved_by": version.approved_by,
                    "approved_at": version.approved_at.isoformat(),
                },
                reason=payload.reason,
            )

            db.commit()
            db.refresh(version)
            return cls.build_schedule_response(db, version)
        except Exception:
            db.rollback()
            raise

    @classmethod
    def reject_schedule(
        cls,
        db: Session,
        schedule_id: uuid.UUID,
        payload: ScheduleRejectRequest,
    ) -> ScheduleGenerationResponse:
        """Human rejection by Operations Manager: marks DRAFT proposal as REJECTED without touching ACTIVE schedule."""
        version = db.get(ScheduleVersion, schedule_id)
        if not version:
            raise NotFoundException("ScheduleVersion", schedule_id)

        if version.status == ScheduleVersionStatus.ACTIVE.value:
            raise ConflictException(
                code="INVALID_SCHEDULE_STATE",
                message="Cannot reject the currently ACTIVE production schedule.",
                details=[{"schedule_id": str(schedule_id), "status": version.status}],
            )

        prev_status = version.status
        version.status = ScheduleVersionStatus.REJECTED.value
        version.approved_by = payload.rejected_by.strip()
        version.approved_at = datetime.now(timezone.utc)
        version.decision_reason = payload.reason.strip()

        AuditService.log_event(
            db,
            schedule_version_id=version.id,
            entity_type="SCHEDULE_VERSION",
            entity_id=version.id,
            action="REJECT_PROPOSAL",
            old_value={"status": prev_status},
            new_value={
                "status": ScheduleVersionStatus.REJECTED.value,
                "rejected_by": payload.rejected_by.strip(),
            },
            reason=payload.reason,
        )
        db.commit()
        db.refresh(version)
        return cls.build_schedule_response(db, version)

    @classmethod
    def get_schedule_by_id(
        cls,
        db: Session,
        schedule_id: uuid.UUID,
    ) -> ScheduleGenerationResponse:
        """Get a specific schedule version by ID."""
        version = db.get(ScheduleVersion, schedule_id)
        if not version:
            raise NotFoundException("ScheduleVersion", schedule_id)
        return cls.build_schedule_response(db, version)

    @classmethod
    def get_current_schedule(cls, db: Session) -> ScheduleGenerationResponse:
        """Get the currently ACTIVE schedule version or raise 404."""
        active = cls.get_current_active_version(db)
        if not active:
            raise NotFoundException("Active ScheduleVersion", "current")
        return cls.build_schedule_response(db, active)

    @staticmethod
    def list_schedule_versions(
        db: Session,
        status: ScheduleVersionStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ScheduleVersion]:
        """List all schedule versions ordered by version_number descending."""
        stmt = select(ScheduleVersion).order_by(ScheduleVersion.version_number.desc())
        if status is not None:
            stmt = stmt.where(ScheduleVersion.status == status.value)
        return list(db.scalars(stmt.offset(skip).limit(limit)).all())

    @staticmethod
    def list_scheduling_runs(
        db: Session,
        run_type: SchedulingRunType | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SchedulingRun]:
        """List scheduling runs ordered by created_at descending."""
        stmt = select(SchedulingRun).order_by(SchedulingRun.created_at.desc())
        if run_type is not None:
            stmt = stmt.where(SchedulingRun.run_type == run_type.value)
        return list(db.scalars(stmt.offset(skip).limit(limit)).all())

    @staticmethod
    def get_scheduling_run_by_id(db: Session, run_id: uuid.UUID) -> SchedulingRun:
        """Get a specific SchedulingRun by ID or raise 404."""
        run = db.get(SchedulingRun, run_id)
        if not run:
            raise NotFoundException("SchedulingRun", run_id)
        return run

    @classmethod
    def rank_candidates(
        cls,
        db: Session,
        request: CandidateRankingRequest,
    ) -> CandidateRankingResponse:
        """Rank feasible technicians for a job using ConstraintValidator and CandidateScorer."""
        job = db.get(Job, request.job_id)
        if not job:
            raise NotFoundException("Job", request.job_id)

        if request.reference_schedule_version_id:
            ref_version = db.get(ScheduleVersion, request.reference_schedule_version_id)
            if not ref_version:
                raise NotFoundException(
                    "ScheduleVersion", request.reference_schedule_version_id
                )
        else:
            ref_version = cls.get_current_active_version(db)

        existing_assigns = list(ref_version.assignments or []) if ref_version else []
        parent_lookup = {a.job_id: a for a in existing_assigns}
        all_techs = list(
            db.scalars(select(Technician).order_by(Technician.name.asc())).all()
        )

        return CandidateScorer.rank_candidates_for_job(
            job=job,
            technicians=all_techs,
            existing_assignments=existing_assigns,
            parent_assignments_by_job=parent_lookup,
            requested_start_time=request.planned_start_time,
        )

    @classmethod
    def validate_proposed_schedule(
        cls,
        db: Session,
        request: ScheduleValidationRequest,
    ) -> ScheduleValidationResponse:
        """Run centralized ConstraintValidator on a proposed assignment bundle."""
        parent_version = (
            db.get(ScheduleVersion, request.parent_version_id)
            if request.parent_version_id
            else cls.get_current_active_version(db)
        )
        all_jobs = {j.id: j for j in db.scalars(select(Job)).all()}
        all_techs = {t.id: t for t in db.scalars(select(Technician)).all()}

        violations = ConstraintValidator.validate_schedule_bundle(
            assignments=request.proposed_assignments,
            jobs_by_id=all_jobs,
            technicians_by_id=all_techs,
            parent_schedule=parent_version,
        )
        return ScheduleValidationResponse(
            is_valid=len(violations) == 0,
            violations_count=len(violations),
            violations=violations,
        )

