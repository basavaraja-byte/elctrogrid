"""SchedulerEngineAdapter: Implements SchedulerEngineProtocol connecting BDSC persistence with DispatchGrid Optimization & Recovery Engine."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import logging
from typing import Any
import uuid

from app.models.assignment import Assignment
from app.models.enums import AssignmentStatus, JobPriority, JobStatus
from app.models.job import Job as DBJob
from app.models.schedule import ScheduleVersion
from app.models.technician import Technician as DBTechnician
from app.schemas.assignment import ProposedAssignmentInput
from app.schemas.schedule import (
    ScheduleGenerateRequest,
    UnassignedJobReasonSchema,
)
from app.scheduler.engine import generate_schedule
from app.schemas.scheduling import (
    Electrician,
    ExistingAssignment,
    Job as SchedJob,
    PriorityLevel,
    SchedulerConfig,
    UnavailabilityInterval,
    normalize_priority,
)
from app.ai.schemas import JobDurationPredictionRequest
from app.ai.services import ai_service
from app.utils.validators import ensure_timezone_aware

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))


class SchedulerEngineAdapter:
    """Production adapter bridging BDSC database entities with the Module B/C scheduling and optimization algorithms."""

    def solve(
        self,
        *,
        jobs: list[DBJob],
        technicians: list[DBTechnician],
        parent_schedule: ScheduleVersion | None,
        request: ScheduleGenerateRequest,
    ) -> tuple[list[ProposedAssignmentInput], list[UnassignedJobReasonSchema]]:
        """Execute deterministic greedy scheduling and bounded local search optimization, returning proposed assignments."""
        if not jobs or not technicians:
            return [], []

        # Reference service date and timezone (IST +05:30)
        ref_date = getattr(request, "service_date", None)
        if ref_date is None:
            if getattr(request, "horizon_start", None) is not None:
                ref_date = request.horizon_start.date()
            elif jobs:
                ref_date = jobs[0].appointment_window_start.date()
            else:
                ref_date = date(2026, 10, 30)

        service_midnight = datetime(ref_date.year, ref_date.month, ref_date.day, 0, 0, 0, tzinfo=IST)

        def dt_to_min(dt: datetime | None) -> int:
            if dt is None:
                return 0
            aware_dt = ensure_timezone_aware(dt).astimezone(IST)
            delta = (aware_dt - service_midnight).total_seconds()
            return int(round(delta / 60.0))

        def min_to_dt(minutes: int) -> datetime:
            return service_midnight + timedelta(minutes=minutes)

        # 1. Map DB Technicians -> Scheduler Electricians
        sched_elecs: list[Electrician] = []
        unavail_list: list[UnavailabilityInterval] = []

        for t in technicians:
            shift_start_min = t.shift_start.hour * 60 + t.shift_start.minute
            shift_end_min = t.shift_end.hour * 60 + t.shift_end.minute

            start_x = round((t.longitude - 77.5) * 100.0, 2)
            start_y = round((t.latitude - 12.9) * 100.0, 2)

            is_active_flag = t.is_active and (t.availability_status != "OFF_DUTY")
            status_str = "active" if is_active_flag else "inactive"

            sched_elecs.append(
                Electrician(
                    technician_id=str(t.id),
                    name=t.name,
                    trade="electrician",
                    skills=list(t.skills or []),
                    certifications=["CHESCOM Certified", "Wireman License"],
                    eligible_zones=list(t.service_zones or []),
                    home_zone=t.service_zones[0] if t.service_zones else "Central",
                    shift_start_min=shift_start_min,
                    shift_end_min=shift_end_min,
                    start_x_km=start_x,
                    start_y_km=start_y,
                    status=status_str,
                )
            )

            # Map unavailable windows
            for idx, uw in enumerate(t.unavailable_windows or []):
                try:
                    u_start = ensure_timezone_aware(datetime.fromisoformat(uw["start"]))
                    u_end = ensure_timezone_aware(datetime.fromisoformat(uw["end"]))
                    unavail_list.append(
                        UnavailabilityInterval(
                            unavailability_id=f"unavail-{t.id}-{idx}",
                            technician_id=str(t.id),
                            start_min=dt_to_min(u_start),
                            end_min=dt_to_min(u_end),
                            reason=uw.get("reason", "Unavailable"),
                        )
                    )
                except Exception as exc:
                    logger.debug("Failed parsing unavailable window for tech %s: %s", t.id, exc)

        # 2. Map DB Jobs -> Scheduler Jobs (Include all non-cancelled jobs)
        sched_jobs: list[SchedJob] = []
        for j in jobs:
            if j.status == JobStatus.CANCELLED.value:
                continue

            prio = normalize_priority(j.priority)
            loc_x = round((j.longitude - 77.5) * 100.0, 2)
            loc_y = round((j.latitude - 12.9) * 100.0, 2)

            dur = max(1, j.estimated_duration_minutes)
            ws = dt_to_min(j.appointment_window_start)
            raw_we = dt_to_min(j.appointment_window_end)
            sla = dt_to_min(j.sla_deadline) if j.sla_deadline else raw_we

            # AI-enhanced duration prediction for mutable tickets when enabled (strictly protect immutable commitments)
            is_immutable = (j.status in (JobStatus.COMPLETED.value, JobStatus.IN_PROGRESS.value))
            use_ai = getattr(request, "use_ai_durations", False)
            if use_ai and not is_immutable:
                try:
                    ai_pred = ai_service.predict_duration(
                        JobDurationPredictionRequest(
                            job_type=j.job_type,
                            priority=prio,
                            required_skills=list(j.required_skills or []),
                            service_zone=j.service_zone,
                            window_start_min=ws,
                            window_end_min=raw_we,
                            sla_deadline_min=sla,
                            estimated_duration_min=dur,
                        )
                    )
                    if not ai_pred.fallback_used and ai_pred.predicted_duration_min > 0:
                        pred_int = int(round(ai_pred.predicted_duration_min))
                        max_window_span = max(15, raw_we - ws)
                        if pred_int <= max_window_span:
                            dur = pred_int
                except Exception as exc:
                    logger.debug("AI duration prediction skipped for job %s: %s", j.id, exc)

            we = max(ws, raw_we - dur)

            sched_jobs.append(
                SchedJob(
                    job_id=str(j.id),
                    trade="electrician",
                    job_type=j.job_type,
                    required_skills=list(j.required_skills or []),
                    priority=prio,
                    duration_min=dur,
                    zone=j.service_zone,
                    location_x_km=loc_x,
                    location_y_km=loc_y,
                    window_start_min=ws,
                    window_end_min=we,
                    sla_deadline_min=sla,
                    status=j.status.lower(),
                    notes=j.description or "",
                )
            )

        # 3. Map parent schedule locked commitments
        existing_commitments: list[ExistingAssignment] = []
        jobs_by_id = {j.id: j for j in jobs}
        if parent_schedule and parent_schedule.assignments:
            for a in parent_schedule.assignments:
                j = jobs_by_id.get(a.job_id)
                if not j:
                    continue
                dur = j.estimated_duration_minutes or 60
                is_locked = (j.status in (JobStatus.COMPLETED.value, JobStatus.IN_PROGRESS.value))
                existing_commitments.append(
                    ExistingAssignment(
                        assignment_id=str(a.id),
                        job_id=str(a.job_id),
                        technician_id=str(a.technician_id),
                        planned_start_min=dt_to_min(a.planned_start_time),
                        duration_min=dur,
                        status=a.assignment_status.lower(),
                        locked=bool(is_locked),
                    )
                )

        # 4. Configure optimization engine
        enable_opt = getattr(request, "enable_optimization", True)
        config = SchedulerConfig(
            service_date=ref_date,
            enable_optimization=bool(enable_opt),
            allow_coordinate_travel_fallback=True,
            urgency_horizon_min=240.0,
            protect_in_progress=True,
        )

        # 5. Run the core Scheduling & Optimization Engine
        run_res = generate_schedule(
            jobs=sched_jobs,
            electricians=sched_elecs,
            travel_times=[],  # Coordinate Euclidean detour matrix
            existing_assignments=existing_commitments,
            unavailability=unavail_list,
            config=config,
            run_id=f"run-{uuid.uuid4().hex[:12]}",
        )

        active_snapshot = run_res.final_schedule if enable_opt else run_res.initial_greedy_schedule
        proposed: list[ProposedAssignmentInput] = []

        # 6. Translate assignments to ProposedAssignmentInput
        for sa in active_snapshot.assignments:
            start_dt = min_to_dt(sa.planned_start_min)
            end_dt = min_to_dt(sa.completion_min)
            if end_dt <= start_dt:
                end_dt = start_dt + timedelta(minutes=60)

            reason_str = "Assigned by bounded local-search optimization engine"
            if hasattr(sa, "explanation") and sa.explanation:
                if hasattr(sa.explanation, "selection_reason"):
                    reason_str = f"{sa.explanation.selection_reason}. {getattr(sa.explanation, 'route_impact', '')}".strip()
                else:
                    reason_str = str(sa.explanation)

            proposed.append(
                ProposedAssignmentInput(
                    job_id=uuid.UUID(sa.job_id),
                    technician_id=uuid.UUID(sa.technician_id),
                    planned_start_time=start_dt,
                    planned_end_time=end_dt,
                    estimated_travel_minutes=sa.travel_time_min or 0,
                    assignment_status=AssignmentStatus.PLANNED,
                    assignment_reason=reason_str[:990],
                )
            )

        # 7. Translate unassigned diagnostics
        unassigned_reasons: list[UnassignedJobReasonSchema] = []
        for ur in active_snapshot.unassigned_reports:
            try:
                unassigned_reasons.append(
                    UnassignedJobReasonSchema(
                        job_id=uuid.UUID(ur.job_id),
                        reason_code=ur.primary_reason_code.value,
                        explanation=ur.explanation,
                    )
                )
            except Exception:
                pass

        return proposed, unassigned_reasons
