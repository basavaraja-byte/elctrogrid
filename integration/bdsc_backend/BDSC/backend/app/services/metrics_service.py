"""Persisted schedule metrics and before-and-after comparison service (Mandatory Addition #7)."""

import math
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.assignment import Assignment
from app.models.enums import (
    AssignmentChangeType,
    JobStatus,
    ScheduleVersionStatus,
    SLARiskLevel,
)
from app.models.job import Job
from app.models.schedule import ScheduleVersion
from app.models.technician import Technician
from app.schemas.schedule import (
    AssignmentDiffItem,
    ScheduleComparisonResponse,
    ScheduleMetricsDelta,
    ScheduleMetricsResponse,
    SLARiskInfoSchema,
    TechnicianWorkloadItem,
    WorkloadDistributionSummary,
)
from app.services.constraint_validator import ConstraintValidator
from app.utils.validators import compute_shift_duration_minutes, ensure_timezone_aware


class MetricsService:
    """Computes actual schedule metrics and version comparisons strictly from persisted database rows."""

    @staticmethod
    def compute_sla_risks(
        assignments: list[Assignment],
        jobs_by_id: dict[uuid.UUID, Job],
    ) -> list[SLARiskInfoSchema]:
        """Calculate SLA buffer and risk level for each persisted assignment."""
        risks: list[SLARiskInfoSchema] = []
        for assign in assignments:
            job = jobs_by_id.get(assign.job_id)
            if not job:
                continue
            sla_dt = ensure_timezone_aware(job.sla_deadline)
            end_dt = ensure_timezone_aware(assign.planned_end_time)
            buffer_mins = int(round((sla_dt - end_dt).total_seconds() / 60.0))
            is_late = buffer_mins < 0

            if is_late:
                risk_level = SLARiskLevel.BREACHED
            elif buffer_mins <= 30:
                risk_level = SLARiskLevel.HIGH
            elif buffer_mins <= 60:
                risk_level = SLARiskLevel.MEDIUM
            else:
                risk_level = SLARiskLevel.LOW

            risks.append(
                SLARiskInfoSchema(
                    job_id=job.id,
                    sla_deadline=sla_dt,
                    planned_end_time=end_dt,
                    buffer_minutes=buffer_mins,
                    risk_level=risk_level,
                    is_late=is_late,
                )
            )
        return risks

    @classmethod
    def calculate_schedule_metrics(
        cls,
        db: Session,
        schedule_id: uuid.UUID,
    ) -> ScheduleMetricsResponse:
        """Compute comprehensive schedule metrics from persisted database rows."""
        version = db.get(ScheduleVersion, schedule_id)
        if not version:
            raise NotFoundException("ScheduleVersion", schedule_id)

        all_jobs = list(db.scalars(select(Job)).all())
        jobs_by_id: dict[uuid.UUID, Job] = {j.id: j for j in all_jobs}
        active_scope_jobs = [
            j for j in all_jobs if j.status != JobStatus.CANCELLED.value
        ]

        all_techs = list(
            db.scalars(select(Technician).order_by(Technician.name.asc())).all()
        )
        techs_by_id: dict[uuid.UUID, Technician] = {t.id: t for t in all_techs}

        assignments = list(version.assignments or [])
        assigned_job_ids = {a.job_id for a in assignments}

        total_jobs_in_scope = len(active_scope_jobs)
        assigned_count = len(assignments)
        unassigned_count = sum(
            1 for j in active_scope_jobs if j.id not in assigned_job_ids
        )

        # SLA compliance
        sla_risks = cls.compute_sla_risks(assignments, jobs_by_id)
        sla_breached = sum(1 for r in sla_risks if r.is_late)
        sla_at_risk = sum(
            1 for r in sla_risks if not r.is_late and r.risk_level == SLARiskLevel.HIGH
        )
        sla_compliant = assigned_count - sla_breached
        sla_compliance_rate = (
            round((sla_compliant / assigned_count) * 100.0, 2)
            if assigned_count > 0
            else 100.0
        )

        total_travel_mins = sum(max(0, a.estimated_travel_minutes or 0) for a in assignments)

        # Technician workload distribution
        assigns_by_tech: dict[uuid.UUID, list[Assignment]] = {}
        for a in assignments:
            assigns_by_tech.setdefault(a.technician_id, []).append(a)

        per_tech_items: list[TechnicianWorkloadItem] = []
        active_utilizations: list[float] = []

        for tech in all_techs:
            tech_assigns = assigns_by_tech.get(tech.id, [])
            try:
                shift_mins = compute_shift_duration_minutes(tech.shift_start, tech.shift_end)
            except Exception:
                shift_mins = 480

            work_mins = sum(
                max(
                    0,
                    int(
                        round(
                            (
                                ensure_timezone_aware(a.planned_end_time)
                                - ensure_timezone_aware(a.planned_start_time)
                            ).total_seconds()
                            / 60.0
                        )
                    ),
                )
                for a in tech_assigns
            )
            travel_mins = sum(max(0, a.estimated_travel_minutes or 0) for a in tech_assigns)
            busy_mins = work_mins + travel_mins
            util_pct = (
                round((busy_mins / shift_mins) * 100.0, 2) if shift_mins > 0 else 0.0
            )

            if tech.is_active:
                active_utilizations.append(util_pct)

            per_tech_items.append(
                TechnicianWorkloadItem(
                    technician_id=tech.id,
                    technician_name=tech.name,
                    is_active=tech.is_active,
                    shift_duration_minutes=shift_mins,
                    assigned_job_count=len(tech_assigns),
                    total_work_minutes=work_mins,
                    total_travel_minutes=travel_mins,
                    total_busy_minutes=busy_mins,
                    utilization_pct=util_pct,
                )
            )

        if active_utilizations:
            min_util = round(min(active_utilizations), 2)
            max_util = round(max(active_utilizations), 2)
            avg_util = round(sum(active_utilizations) / len(active_utilizations), 2)
            variance = sum((u - avg_util) ** 2 for u in active_utilizations) / len(
                active_utilizations
            )
            std_dev_util = round(math.sqrt(variance), 2)
        else:
            min_util = max_util = avg_util = std_dev_util = 0.0

        workload_summary = WorkloadDistributionSummary(
            technicians_evaluated=len(active_utilizations),
            min_utilization_pct=min_util,
            max_utilization_pct=max_util,
            avg_utilization_pct=avg_util,
            std_dev_utilization_pct=std_dev_util,
            per_technician=per_tech_items,
        )

        # Hard-constraint violations check against parent version (if any)
        parent_version = (
            db.get(ScheduleVersion, version.parent_version_id)
            if version.parent_version_id
            else None
        )
        violations = ConstraintValidator.validate_schedule_bundle(
            assignments=assignments,
            jobs_by_id=jobs_by_id,
            technicians_by_id=techs_by_id,
            parent_schedule=parent_version,
        )

        return ScheduleMetricsResponse(
            schedule_version_id=version.id,
            version_number=version.version_number,
            status=ScheduleVersionStatus(version.status),
            total_jobs_in_scope=total_jobs_in_scope,
            assigned_jobs_count=assigned_count,
            unassigned_jobs_count=unassigned_count,
            sla_compliant_count=sla_compliant,
            sla_at_risk_count=sla_at_risk,
            sla_breached_count=sla_breached,
            sla_compliance_rate_pct=sla_compliance_rate,
            total_estimated_travel_minutes=total_travel_mins,
            technician_workload_distribution=workload_summary,
            hard_constraint_violations_count=len(violations),
            hard_constraint_violations=violations,
        )

    @classmethod
    def compare_schedules(
        cls,
        db: Session,
        base_schedule_id: uuid.UUID,
        target_schedule_id: uuid.UUID,
    ) -> ScheduleComparisonResponse:
        """Compute before-and-after metrics and per-job assignment diffs between two schedule versions."""
        base_version = db.get(ScheduleVersion, base_schedule_id)
        if not base_version:
            raise NotFoundException("ScheduleVersion", base_schedule_id)

        target_version = db.get(ScheduleVersion, target_schedule_id)
        if not target_version:
            raise NotFoundException("ScheduleVersion", target_schedule_id)

        base_metrics = cls.calculate_schedule_metrics(db, base_schedule_id)
        target_metrics = cls.calculate_schedule_metrics(db, target_schedule_id)

        all_jobs = list(db.scalars(select(Job)).all())
        jobs_by_id: dict[uuid.UUID, Job] = {j.id: j for j in all_jobs}

        base_by_job: dict[uuid.UUID, Assignment] = {
            a.job_id: a for a in (base_version.assignments or [])
        }
        target_by_job: dict[uuid.UUID, Assignment] = {
            a.job_id: a for a in (target_version.assignments or [])
        }

        all_involved_job_ids = sorted(
            set(base_by_job.keys()) | set(target_by_job.keys()),
            key=lambda x: str(x),
        )

        diffs: list[AssignmentDiffItem] = []
        changed_count = 0
        unchanged_count = 0

        for jid in all_involved_job_ids:
            job = jobs_by_id.get(jid)
            job_status = job.status if job else "UNKNOWN"
            b_assign = base_by_job.get(jid)
            t_assign = target_by_job.get(jid)

            if b_assign is None and t_assign is not None:
                changed_count += 1
                diffs.append(
                    AssignmentDiffItem(
                        job_id=jid,
                        job_status=job_status,
                        change_type=AssignmentChangeType.NEWLY_ASSIGNED,
                        base_technician_id=None,
                        target_technician_id=t_assign.technician_id,
                        base_planned_start_time=None,
                        target_planned_start_time=ensure_timezone_aware(
                            t_assign.planned_start_time
                        ),
                        base_planned_end_time=None,
                        target_planned_end_time=ensure_timezone_aware(
                            t_assign.planned_end_time
                        ),
                        time_shift_minutes=0,
                    )
                )
            elif b_assign is not None and t_assign is None:
                changed_count += 1
                diffs.append(
                    AssignmentDiffItem(
                        job_id=jid,
                        job_status=job_status,
                        change_type=AssignmentChangeType.NEWLY_UNASSIGNED,
                        base_technician_id=b_assign.technician_id,
                        target_technician_id=None,
                        base_planned_start_time=ensure_timezone_aware(
                            b_assign.planned_start_time
                        ),
                        target_planned_start_time=None,
                        base_planned_end_time=ensure_timezone_aware(
                            b_assign.planned_end_time
                        ),
                        target_planned_end_time=None,
                        time_shift_minutes=0,
                    )
                )
            elif b_assign is not None and t_assign is not None:
                b_start = ensure_timezone_aware(b_assign.planned_start_time)
                t_start = ensure_timezone_aware(t_assign.planned_start_time)
                b_end = ensure_timezone_aware(b_assign.planned_end_time)
                t_end = ensure_timezone_aware(t_assign.planned_end_time)
                shift_mins = int(round((t_start - b_start).total_seconds() / 60.0))

                if b_assign.technician_id != t_assign.technician_id:
                    changed_count += 1
                    c_type = AssignmentChangeType.REASSIGNED_TECHNICIAN
                elif shift_mins != 0 or b_end != t_end:
                    changed_count += 1
                    c_type = AssignmentChangeType.TIME_SHIFTED
                else:
                    unchanged_count += 1
                    c_type = AssignmentChangeType.UNCHANGED

                diffs.append(
                    AssignmentDiffItem(
                        job_id=jid,
                        job_status=job_status,
                        change_type=c_type,
                        base_technician_id=b_assign.technician_id,
                        target_technician_id=t_assign.technician_id,
                        base_planned_start_time=b_start,
                        target_planned_start_time=t_start,
                        base_planned_end_time=b_end,
                        target_planned_end_time=t_end,
                        time_shift_minutes=shift_mins,
                    )
                )

        deltas = ScheduleMetricsDelta(
            assigned_jobs_delta=(
                target_metrics.assigned_jobs_count - base_metrics.assigned_jobs_count
            ),
            unassigned_jobs_delta=(
                target_metrics.unassigned_jobs_count - base_metrics.unassigned_jobs_count
            ),
            sla_compliance_rate_delta_pct=round(
                target_metrics.sla_compliance_rate_pct
                - base_metrics.sla_compliance_rate_pct,
                2,
            ),
            total_travel_minutes_delta=(
                target_metrics.total_estimated_travel_minutes
                - base_metrics.total_estimated_travel_minutes
            ),
            workload_std_dev_delta_pct=round(
                target_metrics.technician_workload_distribution.std_dev_utilization_pct
                - base_metrics.technician_workload_distribution.std_dev_utilization_pct,
                2,
            ),
            hard_constraint_violations_delta=(
                target_metrics.hard_constraint_violations_count
                - base_metrics.hard_constraint_violations_count
            ),
        )

        return ScheduleComparisonResponse(
            base_schedule_id=base_version.id,
            target_schedule_id=target_version.id,
            base_version_number=base_version.version_number,
            target_version_number=target_version.version_number,
            base_metrics=base_metrics,
            target_metrics=target_metrics,
            deltas=deltas,
            changed_assignments_count=changed_count,
            unchanged_assignments_count=unchanged_count,
            assignment_changes=diffs,
        )

