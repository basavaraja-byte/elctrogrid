"""Centralized hard-constraint validation component (Mandatory Addition #1 & #5).

Reused across:
1. Initial schedule generation (INITIAL)
2. Schedule optimization (OPTIMIZATION)
3. Disruption recovery proposal generation (RECOVERY)
4. Human approval / schedule activation (approve_schedule)
5. Candidate technician ranking (rank_candidates)
"""

from datetime import datetime, timedelta
import uuid

from app.models.assignment import Assignment
from app.models.enums import AvailabilityStatus, JobStatus
from app.models.job import Job
from app.models.schedule import ScheduleVersion
from app.models.technician import Technician
from app.schemas.assignment import ProposedAssignmentInput
from app.schemas.common import ConstraintViolationSchema
from app.utils.validators import (
    ensure_timezone_aware,
    intervals_overlap,
    is_interval_within_shift,
    parse_iso_datetime,
)


class ConstraintValidator:
    """Single canonical source of truth for all hard scheduling and recovery constraints."""

    @classmethod
    def validate_single_assignment(
        cls,
        *,
        job: Job,
        technician: Technician,
        planned_start_time: datetime,
        planned_end_time: datetime,
        estimated_travel_minutes: int = 0,
        allow_cancelled_job: bool = False,
    ) -> list[ConstraintViolationSchema]:
        """Validate all intrinsic hard constraints for assigning `job` to `technician` in `[planned_start_time, planned_end_time)`."""
        violations: list[ConstraintViolationSchema] = []
        ps = ensure_timezone_aware(planned_start_time)
        pe = ensure_timezone_aware(planned_end_time)

        # 0. Job state check
        if not allow_cancelled_job and job.status == JobStatus.CANCELLED.value:
            violations.append(
                ConstraintViolationSchema(
                    code="CANCELLED_JOB_ASSIGNMENT",
                    job_id=job.id,
                    technician_id=technician.id,
                    message=f"Job '{job.id}' is CANCELLED and cannot be scheduled.",
                )
            )

        # 1. Technician active check
        if not technician.is_active:
            violations.append(
                ConstraintViolationSchema(
                    code="INACTIVE_TECHNICIAN",
                    job_id=job.id,
                    technician_id=technician.id,
                    message=f"Technician '{technician.name}' ({technician.id}) is inactive.",
                )
            )

        # 2. Technician global availability state check
        if technician.availability_status == AvailabilityStatus.UNAVAILABLE.value:
            violations.append(
                ConstraintViolationSchema(
                    code="TECHNICIAN_UNAVAILABLE",
                    job_id=job.id,
                    technician_id=technician.id,
                    message=f"Technician '{technician.name}' is marked UNAVAILABLE.",
                )
            )

        # 3. Required skills check
        tech_skills = set(technician.skills or [])
        req_skills = set(job.required_skills or [])
        missing_skills = sorted(req_skills - tech_skills)
        if missing_skills:
            violations.append(
                ConstraintViolationSchema(
                    code="SKILL_MISMATCH",
                    job_id=job.id,
                    technician_id=technician.id,
                    message=(
                        f"Technician '{technician.name}' lacks required skills: "
                        f"{', '.join(missing_skills)}."
                    ),
                    details={"missing_skills": missing_skills},
                )
            )

        # 4. Service zone check
        if job.service_zone not in (technician.service_zones or []):
            violations.append(
                ConstraintViolationSchema(
                    code="ZONE_MISMATCH",
                    job_id=job.id,
                    technician_id=technician.id,
                    message=(
                        f"Technician '{technician.name}' does not cover service zone "
                        f"'{job.service_zone}'."
                    ),
                    details={
                        "job_zone": job.service_zone,
                        "technician_zones": technician.service_zones,
                    },
                )
            )

        # 5. Planned duration check
        if pe <= ps:
            violations.append(
                ConstraintViolationSchema(
                    code="INVALID_PLANNED_WINDOW",
                    job_id=job.id,
                    technician_id=technician.id,
                    message="planned_end_time must be strictly after planned_start_time.",
                )
            )
            return violations

        planned_duration_mins = int(round((pe - ps).total_seconds() / 60.0))
        if planned_duration_mins < job.estimated_duration_minutes:
            violations.append(
                ConstraintViolationSchema(
                    code="INSUFFICIENT_DURATION",
                    job_id=job.id,
                    technician_id=technician.id,
                    message=(
                        f"Planned duration ({planned_duration_mins}m) is shorter than job "
                        f"estimated_duration_minutes ({job.estimated_duration_minutes}m)."
                    ),
                    details={
                        "planned_duration_minutes": planned_duration_mins,
                        "estimated_duration_minutes": job.estimated_duration_minutes,
                    },
                )
            )

        # 6. Appointment window check
        win_start = ensure_timezone_aware(job.appointment_window_start)
        win_end = ensure_timezone_aware(job.appointment_window_end)
        if ps < win_start or pe > win_end:
            violations.append(
                ConstraintViolationSchema(
                    code="APPOINTMENT_WINDOW_VIOLATION",
                    job_id=job.id,
                    technician_id=technician.id,
                    message=(
                        f"Planned interval [{ps.isoformat()}, {pe.isoformat()}] falls outside "
                        f"job appointment window [{win_start.isoformat()}, {win_end.isoformat()}]."
                    ),
                )
            )

        # 7. Shift hours check (including travel lead-in if applicable)
        if not is_interval_within_shift(ps, pe, technician.shift_start, technician.shift_end):
            violations.append(
                ConstraintViolationSchema(
                    code="OUTSIDE_SHIFT_HOURS",
                    job_id=job.id,
                    technician_id=technician.id,
                    message=(
                        f"Planned interval [{ps.isoformat()}, {pe.isoformat()}] falls outside "
                        f"technician shift ({technician.shift_start.isoformat()} - "
                        f"{technician.shift_end.isoformat()})."
                    ),
                )
            )

        # 8. Time-aware unavailable / break windows check
        for win in technician.unavailable_windows or []:
            w_start = parse_iso_datetime(win["start"])
            w_end = parse_iso_datetime(win["end"])
            if intervals_overlap(ps, pe, w_start, w_end):
                w_status = win.get("status", AvailabilityStatus.ON_BREAK.value)
                violations.append(
                    ConstraintViolationSchema(
                        code="UNAVAILABLE_WINDOW_CONFLICT",
                        job_id=job.id,
                        technician_id=technician.id,
                        message=(
                            f"Planned interval overlaps technician {w_status} window "
                            f"[{w_start.isoformat()}, {w_end.isoformat()}] ({win.get('reason', '')})."
                        ),
                    )
                )

        if estimated_travel_minutes < 0:
            violations.append(
                ConstraintViolationSchema(
                    code="NEGATIVE_TRAVEL_TIME",
                    job_id=job.id,
                    technician_id=technician.id,
                    message="estimated_travel_minutes cannot be negative.",
                )
            )

        return violations

    @classmethod
    def validate_recovery_protection(
        cls,
        *,
        parent_schedule: ScheduleVersion | None,
        proposed_assignments: list[ProposedAssignmentInput | Assignment],
        jobs_by_id: dict[uuid.UUID, Job],
    ) -> list[ConstraintViolationSchema]:
        """Enforce Mandatory Addition #5: Never change COMPLETED or IN_PROGRESS jobs relative to parent schedule."""
        violations: list[ConstraintViolationSchema] = []
        proposed_by_job: dict[uuid.UUID, ProposedAssignmentInput | Assignment] = {
            a.job_id: a for a in proposed_assignments
        }

        if parent_schedule is not None:
            parent_by_job: dict[uuid.UUID, Assignment] = {
                a.job_id: a for a in (parent_schedule.assignments or [])
            }
            for job_id, parent_assign in parent_by_job.items():
                job = jobs_by_id.get(job_id)
                if not job:
                    continue
                if job.status in (JobStatus.COMPLETED.value, JobStatus.IN_PROGRESS.value):
                    prop = proposed_by_job.get(job_id)
                    if prop is None:
                        violations.append(
                            ConstraintViolationSchema(
                                code="IMMUTABLE_JOB_VIOLATION",
                                job_id=job.id,
                                technician_id=parent_assign.technician_id,
                                message=(
                                    f"Job '{job.id}' has status '{job.status}' in the active/parent "
                                    "schedule and cannot be unassigned or dropped."
                                ),
                            )
                        )
                        continue

                    p_start = ensure_timezone_aware(parent_assign.planned_start_time)
                    p_end = ensure_timezone_aware(parent_assign.planned_end_time)
                    n_start = ensure_timezone_aware(prop.planned_start_time)
                    n_end = ensure_timezone_aware(prop.planned_end_time)

                    if (
                        prop.technician_id != parent_assign.technician_id
                        or p_start != n_start
                        or p_end != n_end
                    ):
                        violations.append(
                            ConstraintViolationSchema(
                                code="IMMUTABLE_JOB_VIOLATION",
                                job_id=job.id,
                                technician_id=prop.technician_id,
                                message=(
                                    f"Job '{job.id}' is currently '{job.status}' and its assignment "
                                    "(technician or planned times) cannot be altered."
                                ),
                                details={
                                    "original_technician_id": str(parent_assign.technician_id),
                                    "proposed_technician_id": str(prop.technician_id),
                                },
                            )
                        )

        # Also check anyCOMPLETED/IN_PROGRESS job even if there was no parent schedule
        for job_id, prop in proposed_by_job.items():
            job = jobs_by_id.get(job_id)
            if not job:
                continue
            if (
                job.status in (JobStatus.COMPLETED.value, JobStatus.IN_PROGRESS.value)
                and job.assigned_technician_id is not None
                and prop.technician_id != job.assigned_technician_id
            ):
                violations.append(
                    ConstraintViolationSchema(
                        code="IMMUTABLE_JOB_VIOLATION",
                        job_id=job.id,
                        technician_id=prop.technician_id,
                        message=(
                            f"Job '{job.id}' has status '{job.status}' with technician "
                            f"'{job.assigned_technician_id}' and cannot be reassigned to "
                            f"'{prop.technician_id}'."
                        ),
                    )
                )

        return violations

    @classmethod
    def validate_schedule_bundle(
        cls,
        *,
        assignments: list[ProposedAssignmentInput | Assignment],
        jobs_by_id: dict[uuid.UUID, Job],
        technicians_by_id: dict[uuid.UUID, Technician],
        parent_schedule: ScheduleVersion | None = None,
    ) -> list[ConstraintViolationSchema]:
        """Validate an entire schedule's assignments for individual constraints, duplicates, overlaps, and recovery protection."""
        violations: list[ConstraintViolationSchema] = []
        seen_jobs: set[uuid.UUID] = set()
        by_technician: dict[uuid.UUID, list[ProposedAssignmentInput | Assignment]] = {}

        #Build parent immutable job lookup so historic completed/in-progress jobs aren't flagged if unchanged
        parent_assign_by_job: dict[uuid.UUID, Assignment] = {}
        if parent_schedule is not None:
            parent_assign_by_job = {
                a.job_id: a for a in (parent_schedule.assignments or [])
            }

        for item in assignments:
            if item.job_id in seen_jobs:
                violations.append(
                    ConstraintViolationSchema(
                        code="DUPLICATE_JOB_ASSIGNMENT",
                        job_id=item.job_id,
                        technician_id=item.technician_id,
                        message=f"Job '{item.job_id}' is assigned more than once in the same schedule.",
                    )
                )
            seen_jobs.add(item.job_id)

            job = jobs_by_id.get(item.job_id)
            if job is None:
                violations.append(
                    ConstraintViolationSchema(
                        code="JOB_NOT_FOUND",
                        job_id=item.job_id,
                        technician_id=item.technician_id,
                        message=f"Referenced job '{item.job_id}' does not exist.",
                    )
                )
                continue

            tech = technicians_by_id.get(item.technician_id)
            if tech is None:
                violations.append(
                    ConstraintViolationSchema(
                        code="TECHNICIAN_NOT_FOUND",
                        job_id=item.job_id,
                        technician_id=item.technician_id,
                        message=f"Referenced technician '{item.technician_id}' does not exist.",
                    )
                )
                continue

            by_technician.setdefault(item.technician_id, []).append(item)

            # If this job is COMPLETED or IN_PROGRESS and matches its parent assignment identically,
            # skip live technician state/break checks (since work is already underway/finished).
            parent_match = parent_assign_by_job.get(item.job_id)
            if (
                job.status in (JobStatus.COMPLETED.value, JobStatus.IN_PROGRESS.value)
                and parent_match is not None
                and parent_match.technician_id == item.technician_id
                and ensure_timezone_aware(parent_match.planned_start_time)
                == ensure_timezone_aware(item.planned_start_time)
                and ensure_timezone_aware(parent_match.planned_end_time)
                == ensure_timezone_aware(item.planned_end_time)
            ):
                continue

            violations.extend(
                cls.validate_single_assignment(
                    job=job,
                    technician=tech,
                    planned_start_time=item.planned_start_time,
                    planned_end_time=item.planned_end_time,
                    estimated_travel_minutes=item.estimated_travel_minutes,
                )
            )

        # Check per-technician overlapping assignments & travel time buffers
        for tech_id, tech_assignments in by_technician.items():
            sorted_items = sorted(
                tech_assignments,
                key=lambda x: ensure_timezone_aware(x.planned_start_time),
            )
            for idx in range(len(sorted_items) - 1):
                curr_a = sorted_items[idx]
                next_a = sorted_items[idx + 1]
                curr_end = ensure_timezone_aware(curr_a.planned_end_time)
                next_start = ensure_timezone_aware(next_a.planned_start_time)
                next_travel = max(0, next_a.estimated_travel_minutes or 0)

                if curr_end > next_start:
                    violations.append(
                        ConstraintViolationSchema(
                            code="ASSIGNMENT_OVERLAP",
                            job_id=next_a.job_id,
                            technician_id=tech_id,
                            message=(
                                f"Technician '{tech_id}' has overlapping assignments: "
                                f"job '{curr_a.job_id}' ends at {curr_end.isoformat()} after "
                                f"job '{next_a.job_id}' starts at {next_start.isoformat()}."
                            ),
                            details={
                                "first_job_id": str(curr_a.job_id),
                                "second_job_id": str(next_a.job_id),
                            },
                        )
                    )
                elif curr_end + timedelta(minutes=next_travel) > next_start:
                    violations.append(
                        ConstraintViolationSchema(
                            code="INSUFFICIENT_TRAVEL_BUFFER",
                            job_id=next_a.job_id,
                            technician_id=tech_id,
                            message=(
                                f"Technician '{tech_id}' lacks required {next_travel}m travel buffer "
                                f"between job '{curr_a.job_id}' (ends {curr_end.isoformat()}) and "
                                f"job '{next_a.job_id}' (starts {next_start.isoformat()})."
                            ),
                            details={
                                "first_job_id": str(curr_a.job_id),
                                "second_job_id": str(next_a.job_id),
                                "required_travel_minutes": next_travel,
                            },
                        )
                    )

        # Recovery protection check for COMPLETED and IN_PROGRESS jobs
        violations.extend(
            cls.validate_recovery_protection(
                parent_schedule=parent_schedule,
                proposed_assignments=assignments,
                jobs_by_id=jobs_by_id,
            )
        )

        return violations

