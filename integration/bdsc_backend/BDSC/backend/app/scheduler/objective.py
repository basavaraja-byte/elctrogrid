"""Schedule-level objective function and lexicographic comparison hierarchy (Section 9).

Cost formulation:
    C = wT * CT + wS * CS + wW * CW + wR * CR

Units and normalization bounds:
- CT (dimensionless, >= 0): total_travel_min / (N_active_jobs * reference_travel_per_job_min).
  Strictly monotonic in total travel minutes for a fixed job set.
- CS (dimensionless, >= 0): sum(urgency_j / 100) / N_active_jobs (+ soft-breach lateness term
  when soft deadlines are enabled). Captures margin risk before deadline breach and predicted
  lateness when soft deadlines are configured.
- CW (dimensionless, >= 0): population standard deviation of service-only utilization
  (service_min / shift_duration_min) across active electricians + normalized overtime.
  Service time and travel time are tracked separately so travel is never double-counted.
- CR (dimensionless, >= 0): schedule-perturbation units / N_baseline_commitments when
  recovering from a prior schedule; identically 0.0 during initial scheduling.

Hard-deadline vs. Soft-SLA and Coverage Policy (Section 9):
- Hard constraints and hard SLA deadlines (`is_hard_deadline=True`, e.g., `sla_mode='hard'` or
  Critical jobs under `sla_mode='hard_critical_only'`) are enforced strictly BEFORE scoring:
  any candidate exceeding a hard deadline is rejected as infeasible (`SLA_DEADLINE_INFEASIBLE`),
  and `hard_sla_violation_count` sits at Level 3 above coverage.
- Soft SLA deadlines (`is_hard_deadline=False`, e.g., `sla_mode='soft'`) represent target service
  times rather than hard cutoffs. Per Section 9's explicit hierarchy, maximizing feasible job
  coverage while protecting higher-priority jobs (Level 4) strictly precedes reducing soft-SLA
  risk and travel (Level 5). Therefore, assigning a feasible job that incurs a predicted soft-SLA
  breach (`slack_min < 0`) is strictly preferred over leaving that job unassigned.
- Among schedules with identical priority-tiered coverage, fewer `predicted_soft_sla_breach_count`
  and lower weighted cost `C` strictly win. If business policy requires rejecting late service
  outright rather than completing a job past its target, that deadline must be configured as a
  hard deadline (`sla_mode='hard'` or `job.is_hard_deadline=True`).
- `predicted_soft_sla_breach_count` is a planning-time risk projection computed from planned
  completion times; it is never reported as an actual observed SLA violation.

Note: Weights are configurable engineering heuristics, not scientifically calibrated optima.
"""

from __future__ import annotations

import math

from app.scheduler.candidates import InsertionCandidate
from app.scheduler.constraints import (
    FullScheduleValidationResult,
    ResolvedJob,
    RouteStop,
)
from app.scheduler.prioritization import compute_soft_sla_urgency
from app.schemas.scheduling import (
    Electrician,
    ObjectiveBreakdown,
    PriorityLevel,
    SchedulerConfig,
    TechnicianWorkloadSummary,
)


def compute_technician_workloads(
    electricians: list[Electrician],
    routes_by_tech: dict[str, list[RouteStop]],
) -> list[TechnicianWorkloadSummary]:
    """Compute separated service and travel workloads for every technician."""
    summaries: list[TechnicianWorkloadSummary] = []
    for elec in sorted(electricians, key=lambda e: e.technician_id):
        route = routes_by_tech.get(elec.technician_id, [])
        shift_dur = max(1, elec.shift_end_min - elec.shift_start_min)
        service_min = sum(s.job.duration_min for s in route)
        travel_min = sum(s.travel_time_min for s in route)
        duty_min = service_min + travel_min
        overtime_min = 0
        if route:
            overtime_min = max(0, route[-1].completion_min - elec.shift_end_min)

        summaries.append(
            TechnicianWorkloadSummary(
                technician_id=elec.technician_id,
                assigned_job_count=len(route),
                job_ids=[s.job.job_id for s in route],
                shift_start_min=elec.shift_start_min,
                shift_end_min=elec.shift_end_min,
                shift_duration_min=shift_dur,
                planned_service_min=service_min,
                planned_travel_min=travel_min,
                total_duty_min=duty_min,
                service_utilization=round(service_min / float(shift_dur), 6),
                duty_utilization=round(duty_min / float(shift_dur), 6),
                overtime_min=overtime_min,
            )
        )
    return summaries


def _population_std(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean = sum(values) / float(len(values))
    variance = sum((v - mean) ** 2 for v in values) / float(len(values))
    return math.sqrt(variance)


def evaluate_schedule_objective(
    routes_by_tech: dict[str, list[RouteStop]],
    electricians: list[Electrician],
    active_jobs_by_id: dict[str, ResolvedJob],
    validation: FullScheduleValidationResult,
    config: SchedulerConfig,
    baseline_assignments: dict[str, tuple[str, int]] | None = None,
) -> ObjectiveBreakdown:
    """Evaluate all objective components and coverage counts on a schedule state."""
    all_stops: list[RouteStop] = []
    assigned_lookup: dict[str, RouteStop] = {}
    for tid in sorted(routes_by_tech.keys()):
        for stop in routes_by_tech[tid]:
            all_stops.append(stop)
            assigned_lookup[stop.job.job_id] = stop

    n_jobs = max(1, len(active_jobs_by_id))

    # 1. Travel cost (CT)
    raw_travel_min = sum(s.travel_time_min for s in all_stops)
    raw_service_min = sum(s.job.duration_min for s in all_stops)
    travel_denom = float(n_jobs) * config.reference_travel_per_job_min
    ct = raw_travel_min / travel_denom

    # 2. Soft-SLA risk (CS)
    total_urgency = 0.0
    soft_breach_lateness_norm = 0.0
    soft_breach_count = 0
    for stop in all_stops:
        slack = stop.slack_min
        urg = compute_soft_sla_urgency(slack, config.urgency_horizon_min)
        total_urgency += urg
        if slack < 0:
            soft_breach_count += 1
            soft_breach_lateness_norm += abs(slack) / config.urgency_horizon_min

    cs = (total_urgency / 100.0 + soft_breach_lateness_norm) / float(n_jobs)

    # 3. Workload imbalance & overtime (CW) - strictly service utilization to avoid travel double-counting
    active_elecs = [e for e in electricians if e.is_active]
    service_utils: list[float] = []
    total_overtime_min = 0
    total_fleet_shift_min = 0
    for elec in active_elecs:
        route = routes_by_tech.get(elec.technician_id, [])
        s_dur = max(1, elec.shift_end_min - elec.shift_start_min)
        total_fleet_shift_min += s_dur
        s_min = sum(st.job.duration_min for st in route)
        service_utils.append(s_min / float(s_dur))
        if route:
            total_overtime_min += max(0, route[-1].completion_min - elec.shift_end_min)

    util_std = _population_std(service_utils)
    overtime_norm = (
        total_overtime_min / float(max(1, total_fleet_shift_min))
        if total_overtime_min > 0
        else 0.0
    )
    cw = util_std + overtime_norm

    # 4. Schedule-change cost (CR) - zero during initial scheduling when no baseline exists
    raw_change_units = 0.0
    if baseline_assignments:
        for jid, (base_tech, base_start) in baseline_assignments.items():
            if jid not in active_jobs_by_id:
                continue
            cur = assigned_lookup.get(jid)
            if cur is None:
                raw_change_units += 1.5
            elif cur.technician_id != base_tech:
                raw_change_units += 1.0
            elif cur.planned_start_min != base_start:
                shift_diff = abs(cur.planned_start_min - base_start)
                raw_change_units += 0.5 * min(1.0, shift_diff / config.recovery_shift_norm_min)
        cr = raw_change_units / float(max(1, len(baseline_assignments)))
    else:
        cr = 0.0

    weighted_cost = (
        config.w_travel * ct
        + config.w_sla_risk * cs
        + config.w_workload * cw
        + config.w_recovery_change * cr
    )

    unassigned_by_prio: dict[str, int] = {
        PriorityLevel.CRITICAL.value: 0,
        PriorityLevel.HIGH.value: 0,
        PriorityLevel.NORMAL.value: 0,
        PriorityLevel.LOW.value: 0,
    }
    unassigned_total = 0
    for jid, rjob in active_jobs_by_id.items():
        if jid not in assigned_lookup:
            unassigned_total += 1
            unassigned_by_prio[rjob.priority.value] += 1

    return ObjectiveBreakdown(
        weighted_cost=round(weighted_cost, 8),
        travel_cost_norm=round(ct, 8),
        soft_sla_risk_norm=round(cs, 8),
        workload_imbalance_norm=round(cw, 8),
        schedule_change_cost_norm=round(cr, 8),
        w_travel=config.w_travel,
        w_sla_risk=config.w_sla_risk,
        w_workload=config.w_workload,
        w_recovery_change=config.w_recovery_change,
        raw_total_travel_min=raw_travel_min,
        raw_total_service_min=raw_service_min,
        raw_total_soft_sla_urgency=round(total_urgency, 4),
        raw_service_utilization_std=round(util_std, 8),
        raw_total_overtime_min=total_overtime_min,
        raw_schedule_change_units=round(raw_change_units, 4),
        hard_violation_count=validation.hard_violation_count,
        protected_violation_count=validation.protected_violation_count,
        hard_sla_violation_count=validation.hard_sla_violation_count,
        predicted_soft_sla_breach_count=soft_breach_count,
        assigned_count=len(assigned_lookup),
        unassigned_count=unassigned_total,
        unassigned_by_priority=unassigned_by_prio,
    )


def lexicographic_objective_key(
    obj: ObjectiveBreakdown,
) -> tuple[int, int, int, int, int, int, int, int, float, float, float, float, float]:
    """Explicit 7-level lexicographic minimization tuple (Section 9).

    Lower tuple is strictly better:
    1. Hard-constraint violation count (must be 0)
    2. Protected/fixed commitment violation count (must be 0)
    3. Hard SLA violation count (must be 0; hard-deadline-infeasible candidates rejected before scoring)
    4. Unassigned counts ordered deterministically by business priority:
       (Critical, High, Normal, Low) -> maximizes feasible coverage while protecting higher priority,
       including when soft-SLA mode allows assigning a job with negative slack (`slack_min < 0`)
    5. Predicted soft-SLA breach count (planning-time risk indicator among equal-coverage schedules,
       never counted as an actual SLA violation), followed by weighted normalized cost C
       (travel + soft-SLA risk + workload + recovery change)
    6-7. Deterministic component tie-breakers: soft_sla_risk_norm, travel_cost_norm,
         workload_imbalance_norm, and schedule_change_cost_norm.
    """
    ubp = obj.unassigned_by_priority
    return (
        obj.hard_violation_count,
        obj.protected_violation_count,
        obj.hard_sla_violation_count,
        ubp.get(PriorityLevel.CRITICAL.value, 0),
        ubp.get(PriorityLevel.HIGH.value, 0),
        ubp.get(PriorityLevel.NORMAL.value, 0),
        ubp.get(PriorityLevel.LOW.value, 0),
        obj.predicted_soft_sla_breach_count,
        round(obj.weighted_cost, 8),
        round(obj.soft_sla_risk_norm, 8),
        round(obj.travel_cost_norm, 8),
        round(obj.workload_imbalance_norm, 8),
        round(obj.schedule_change_cost_norm, 8),
    )


def is_strictly_better_objective(candidate: ObjectiveBreakdown, incumbent: ObjectiveBreakdown) -> bool:
    """Return True iff candidate is valid and strictly improves the lexicographic objective."""
    if candidate.hard_violation_count > 0 or candidate.protected_violation_count > 0 or candidate.hard_sla_violation_count > 0:
        return False
    return lexicographic_objective_key(candidate) < lexicographic_objective_key(incumbent)


def score_greedy_candidate(
    cand: InsertionCandidate,
    config: SchedulerConfig,
    scarcity_pressure_by_tech: dict[str, float],
    flexible_alternatives_count: int,
    baseline_assignment: tuple[str, int] | None = None,
) -> tuple[int, float, int, int, str, int]:
    """Deterministic candidate comparison key for greedy slot selection.

    Lower tuple is preferred:
    1. Soft SLA breach indicator (0 if slack >= 0 else 1, relevant when soft mode is active)
    2. Incremental normalized weighted cost + scarcity-preservation term
    3. Incremental travel minutes
    4. Planned start time (earlier completion preserves downstream route slack)
    5. Technician ID (deterministic tie-breaker)
    6. Insertion position (deterministic tie-breaker)
    """
    soft_breach = 0 if cand.slack_min >= 0 else 1
    inc_travel_norm = cand.incremental_travel_min / config.reference_travel_per_job_min

    # Include change in downstream soft-SLA urgency across the route
    urg_norm = cand.soft_sla_urgency / 100.0
    if cand.slack_min < 0:
        urg_norm += abs(cand.slack_min) / config.urgency_horizon_min

    work_norm = cand.new_service_utilization

    change_norm = 0.0
    if baseline_assignment is not None:
        base_tech, base_start = baseline_assignment
        if cand.technician_id != base_tech:
            change_norm = 1.0
        elif cand.stop.planned_start_min != base_start:
            change_norm = 0.5 * min(
                1.0,
                abs(cand.stop.planned_start_min - base_start) / config.recovery_shift_norm_min,
            )

    # Scarcity protection: when this job has multiple feasible technicians, avoid consuming
    # bottleneck specialists needed by remaining constrained jobs.
    scarcity_penalty = 0.0
    if flexible_alternatives_count > 1:
        scarcity_penalty = config.scarcity_protection_weight * scarcity_pressure_by_tech.get(
            cand.technician_id, 0.0
        )

    composite = (
        config.w_travel * inc_travel_norm
        + config.w_sla_risk * urg_norm
        + config.w_workload * work_norm
        + config.w_recovery_change * change_norm
        + scarcity_penalty
    )

    return (
        soft_breach,
        round(composite, 8),
        cand.incremental_travel_min,
        cand.stop.planned_start_min,
        cand.technician_id,
        cand.insert_position,
    )

