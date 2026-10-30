"""Feasibility-filtered multi-criteria heuristic candidate scorer (Mandatory Addition #6).

IMPORTANT METHODOLOGY NOTE:
- Strictly filters candidates through the centralized `ConstraintValidator` first.
  Any technician with >= 1 hard-constraint violation is excluded from ranking.
- Ranks feasible technicians using a transparent, weighted linear combination of:
    1. Travel time efficiency (default weight: 0.25)
    2. SLA margin safety (default weight: 0.30)
    3. Job priority alignment (default weight: 0.15)
    4. Technician workload balance (default weight: 0.15)
    5. Schedule stability vs. parent active schedule (default weight: 0.15)
- This module is a local multi-criteria greedy heuristic and explicitly does NOT claim
  global mathematical optimality.
"""

from datetime import datetime, timedelta
import uuid

from app.core.config import settings
from app.models.assignment import Assignment
from app.models.enums import JobPriority, SchedulingStrategy
from app.models.job import Job
from app.models.technician import Technician
from app.schemas.assignment import ProposedAssignmentInput
from app.schemas.schedule import (
    CandidateRankingResponse,
    InfeasibleTechnicianCandidate,
    RankedTechnicianCandidate,
)
from app.services.constraint_validator import ConstraintValidator
from app.utils.validators import (
    compute_shift_duration_minutes,
    ensure_timezone_aware,
    estimate_travel_minutes,
    intervals_overlap,
    is_interval_within_shift,
    parse_iso_datetime,
)

PRIORITY_SCORE_MAP: dict[str, float] = {
    JobPriority.CRITICAL.value: 1.0,
    JobPriority.HIGH.value: 0.75,
    JobPriority.MEDIUM.value: 0.50,
    JobPriority.LOW.value: 0.25,
}


class CandidateScorer:
    """Feasibility-filtered multi-criteria technician ranking heuristic."""

    @staticmethod
    def get_strategy_weights(strategy: SchedulingStrategy | str | None = None) -> dict[str, float]:
        """Return scoring weights for the requested strategy, defaulting to configured weights."""
        if strategy == SchedulingStrategy.MINIMIZE_TRAVEL:
            return {
                "travel_time": 0.45,
                "sla_risk": 0.20,
                "job_priority": 0.10,
                "workload_balance": 0.15,
                "schedule_stability": 0.10,
            }
        if strategy == SchedulingStrategy.SLA_FIRST:
            return {
                "travel_time": 0.15,
                "sla_risk": 0.45,
                "job_priority": 0.20,
                "workload_balance": 0.10,
                "schedule_stability": 0.10,
            }
        if strategy == SchedulingStrategy.STABILITY_FIRST:
            return {
                "travel_time": 0.15,
                "sla_risk": 0.25,
                "job_priority": 0.10,
                "workload_balance": 0.10,
                "schedule_stability": 0.40,
            }
        return settings.scoring_weights_dict

    @classmethod
    def find_earliest_feasible_slot(
        cls,
        *,
        job: Job,
        technician: Technician,
        existing_tech_assignments: list[Assignment | ProposedAssignmentInput],
        requested_start: datetime | None = None,
    ) -> tuple[datetime, datetime, int]:
        """Find the earliest slot within the job's appointment window that avoids overlaps and breaks."""
        win_start = ensure_timezone_aware(job.appointment_window_start)
        win_end = ensure_timezone_aware(job.appointment_window_end)
        candidate_start = ensure_timezone_aware(requested_start) if requested_start else win_start
        if candidate_start < win_start:
            candidate_start = win_start

        duration_delta = timedelta(minutes=job.estimated_duration_minutes)
        sorted_existing = sorted(
            existing_tech_assignments,
            key=lambda a: ensure_timezone_aware(a.planned_start_time),
        )

        # Iteratively push candidate_start forward if blocked by an existing assignment or break
        for _ in range(25):
            candidate_end = candidate_start + duration_delta

            # Determine origin coordinates for travel calculation
            prev_assigns = [
                a
                for a in sorted_existing
                if ensure_timezone_aware(a.planned_end_time) <= candidate_start
            ]
            travel_mins = estimate_travel_minutes(
                technician.latitude,
                technician.longitude,
                job.latitude,
                job.longitude,
            )

            if prev_assigns:
                last_prev = prev_assigns[-1]
                earliest_after_prev = ensure_timezone_aware(
                    last_prev.planned_end_time
                ) + timedelta(minutes=travel_mins)
                if candidate_start < earliest_after_prev:
                    candidate_start = earliest_after_prev
                    continue

            # Check overlap with any existing assignment
            bumped = False
            for ex in sorted_existing:
                ex_start = ensure_timezone_aware(ex.planned_start_time)
                ex_end = ensure_timezone_aware(ex.planned_end_time)
                ex_travel = max(0, ex.estimated_travel_minutes or 0)
                if intervals_overlap(
                    candidate_start,
                    candidate_end + timedelta(minutes=ex_travel),
                    ex_start,
                    ex_end,
                ):
                    candidate_start = ex_end + timedelta(minutes=travel_mins)
                    bumped = True
                    break
            if bumped:
                continue

            # Check overlap with technician unavailable/break windows
            for win in technician.unavailable_windows or []:
                w_start = parse_iso_datetime(win["start"])
                w_end = parse_iso_datetime(win["end"])
                if intervals_overlap(candidate_start, candidate_end, w_start, w_end):
                    candidate_start = w_end
                    bumped = True
                    break
            if bumped:
                continue

            # If candidate_end fits within appointment window & shift, return it
            if candidate_end <= win_end and is_interval_within_shift(
                candidate_start, candidate_end, technician.shift_start, technician.shift_end
            ):
                return candidate_start, candidate_end, travel_mins
            break

        # Fallback to requested/window start so ConstraintValidator can record the exact violation reason
        fallback_start = ensure_timezone_aware(requested_start) if requested_start else win_start
        fallback_end = fallback_start + duration_delta
        fallback_travel = estimate_travel_minutes(
            technician.latitude,
            technician.longitude,
            job.latitude,
            job.longitude,
        )
        return fallback_start, fallback_end, fallback_travel

    @classmethod
    def rank_candidates_for_job(
        cls,
        *,
        job: Job,
        technicians: list[Technician],
        existing_assignments: list[Assignment | ProposedAssignmentInput],
        parent_assignments_by_job: dict[uuid.UUID, Assignment] | None = None,
        requested_start_time: datetime | None = None,
        strategy: SchedulingStrategy = SchedulingStrategy.BALANCED,
    ) -> CandidateRankingResponse:
        """Filter technicians via ConstraintValidator and rank feasible candidates."""
        weights = cls.get_strategy_weights(strategy)
        parent_lookup = parent_assignments_by_job or {}
        parent_assign = parent_lookup.get(job.id)

        by_tech: dict[uuid.UUID, list[Assignment | ProposedAssignmentInput]] = {}
        for a in existing_assignments:
            if a.job_id != job.id:
                by_tech.setdefault(a.technician_id, []).append(a)

        feasible: list[RankedTechnicianCandidate] = []
        infeasible: list[InfeasibleTechnicianCandidate] = []

        for tech in technicians:
            tech_existing = by_tech.get(tech.id, [])
            if requested_start_time is not None:
                p_start = ensure_timezone_aware(requested_start_time)
                p_end = p_start + timedelta(minutes=job.estimated_duration_minutes)
                travel_mins = estimate_travel_minutes(
                    tech.latitude, tech.longitude, job.latitude, job.longitude
                )
            else:
                p_start, p_end, travel_mins = cls.find_earliest_feasible_slot(
                    job=job,
                    technician=tech,
                    existing_tech_assignments=tech_existing,
                )

            # Evaluate single-assignment hard constraints + overlap with tech_existing
            violations = ConstraintValidator.validate_single_assignment(
                job=job,
                technician=tech,
                planned_start_time=p_start,
                planned_end_time=p_end,
                estimated_travel_minutes=travel_mins,
            )

            # Also verify no overlap or travel buffer violation with tech_existing
            for ex in tech_existing:
                ex_start = ensure_timezone_aware(ex.planned_start_time)
                ex_end = ensure_timezone_aware(ex.planned_end_time)
                if intervals_overlap(p_start, p_end, ex_start, ex_end):
                    from app.schemas.common import ConstraintViolationSchema

                    violations.append(
                        ConstraintViolationSchema(
                            code="ASSIGNMENT_OVERLAP",
                            job_id=job.id,
                            technician_id=tech.id,
                            message=(
                                f"Overlaps existing assignment for job '{ex.job_id}' "
                                f"[{ex_start.isoformat()}, {ex_end.isoformat()}]."
                            ),
                        )
                    )
                elif ex_end <= p_start and ex_end + timedelta(minutes=travel_mins) > p_start:
                    from app.schemas.common import ConstraintViolationSchema

                    violations.append(
                        ConstraintViolationSchema(
                            code="INSUFFICIENT_TRAVEL_BUFFER",
                            job_id=job.id,
                            technician_id=tech.id,
                            message=(
                                f"Requires {travel_mins}m travel after job '{ex.job_id}' "
                                f"ending at {ex_end.isoformat()}."
                            ),
                        )
                    )

            if violations:
                infeasible.append(
                    InfeasibleTechnicianCandidate(
                        technician_id=tech.id,
                        technician_name=tech.name,
                        violations=violations,
                    )
                )
                continue

            # Compute normalized component scores in [0.0, 1.0]
            # 1. Travel score: 0 min -> 1.0, >= 60 min -> 0.0
            s_travel = max(0.0, min(1.0, 1.0 - (travel_mins / 60.0)))

            # 2. SLA margin score: >= 120m buffer -> 1.0, <= 0m buffer -> 0.0
            sla_deadline = ensure_timezone_aware(job.sla_deadline)
            sla_buffer_mins = (sla_deadline - p_end).total_seconds() / 60.0
            if sla_buffer_mins < 0:
                s_sla = 0.0
            else:
                s_sla = min(1.0, sla_buffer_mins / 120.0)

            # 3. Priority alignment score: rewards earlier start within window weighted by priority
            win_start = ensure_timezone_aware(job.appointment_window_start)
            win_end = ensure_timezone_aware(job.appointment_window_end)
            slack_Total = max(
                1.0,
                ((win_end - win_start).total_seconds() / 60.0) - job.estimated_duration_minutes,
            )
            delay_from_open = max(0.0, (p_start - win_start).total_seconds() / 60.0)
            earliness_factor = max(0.0, min(1.0, 1.0 - (delay_from_open / slack_Total)))
            prio_base = PRIORITY_SCORE_MAP.get(job.priority, 0.5)
            s_priority = round(0.5 * prio_base + 0.5 * earliness_factor, 4)

            # 4. Workload balance score: 1 - current utilization ratio
            try:
                shift_mins = compute_shift_duration_minutes(tech.shift_start, tech.shift_end)
            except Exception:
                shift_mins = 480
            worked_mins = sum(
                max(
                    0.0,
                    (
                        ensure_timezone_aware(a.planned_end_time)
                        - ensure_timezone_aware(a.planned_start_time)
                    ).total_seconds()
                    / 60.0,
                )
                + (a.estimated_travel_minutes or 0)
                for a in tech_existing
            )
            s_workload = max(0.0, min(1.0, 1.0 - (worked_mins / max(1, shift_mins))))

            # 5. Schedule stability score
            if parent_assign is None:
                s_stability = 1.0
            elif parent_assign.technician_id == tech.id:
                time_diff = abs(
                    (
                        p_start - ensure_timezone_aware(parent_assign.planned_start_time)
                    ).total_seconds()
                    / 60.0
                )
                s_stability = 1.0 if time_diff <= 5.0 else 0.65
            else:
                s_stability = 0.0

            composite = 100.0 * (
                weights["travel_time"] * s_travel
                + weights["sla_risk"] * s_sla
                + weights["job_priority"] * s_priority
                + weights["workload_balance"] * s_workload
                + weights["schedule_stability"] * s_stability
            )

            component_scores = {
                "travel_time": round(s_travel, 4),
                "sla_risk": round(s_sla, 4),
                "job_priority": round(s_priority, 4),
                "workload_balance": round(s_workload, 4),
                "schedule_stability": round(s_stability, 4),
            }

            feasible.append(
                RankedTechnicianCandidate(
                    rank=0,
                    technician_id=tech.id,
                    technician_name=tech.name,
                    planned_start_time=p_start,
                    planned_end_time=p_end,
                    estimated_travel_minutes=travel_mins,
                    composite_score=round(composite, 2),
                    component_scores=component_scores,
                    explanation=(
                        f"Score {composite:.2f}/100 (Travel={travel_mins}m, "
                        f"SLA buffer={int(sla_buffer_mins)}m, "
                        f"Workload={int(worked_mins)}/{shift_mins}m)"
                    ),
                )
            )

        # Sort feasible descending by composite_score, tie-breaking deterministically by travel_minutes then technician_id
        feasible.sort(
            key=lambda c: (-c.composite_score, c.estimated_travel_minutes, str(c.technician_id))
        )
        for idx, cand in enumerate(feasible, start=1):
            cand.rank = idx

        return CandidateRankingResponse(
            job_id=job.id,
            is_globally_optimal=False,
            scoring_weights=weights,
            feasible_candidates=feasible,
            infeasible_candidates=infeasible,
        )

