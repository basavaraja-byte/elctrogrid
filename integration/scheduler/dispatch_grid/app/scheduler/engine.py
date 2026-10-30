"""Core scheduling engine orchestrating Modules B and C (Sections 5, 8, 12, 14).

Workflow:
1. Validate input jobs, technicians, unavailability, and existing commitments.
2. Anchor fixed/protected commitments (completed, in_progress, locked) and preserve
   valid unaffected baseline assignments during recovery.
3. Evaluate static eligibility, deadline urgency, and resource scarcity.
4. Construct a deterministic initial greedy schedule respecting all hard constraints.
5. Improve the schedule using bounded deterministic local search (Module C).
6. Re-validate the entire proposed schedule with the full hard-constraint validator;
   revert safely to the valid greedy schedule if optimization ever fails validation.
7. Generate grounded explanations, unassigned diagnostics, and actual metrics.
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter
from datetime import datetime, timezone

from app.scheduler.candidates import (
    CandidateEvaluationResult,
    StopSpec,
    build_timed_route,
    first_mutable_route_position,
    first_mutable_spec_position,
    generate_candidates_for_job,
    get_static_eligible_electricians,
    stop_to_spec,
)
from app.scheduler.constraints import (
    ConstraintFailure,
    ResolvedJob,
    RouteStop,
    is_historical_or_active_commitment,
    validate_full_schedule,
    validate_job_data,
)
from pathlib import Path

from app.scheduler.dataset_loader import LoadedDatasetBundle, generate_dataset_audit
from app.scheduler.explanations import (
    build_assignment_explanation,
    build_invalid_job_report,
    build_unassigned_job_report,
    compute_incremental_travel_for_stop,
    diff_schedules,
)
from app.scheduler.objective import (
    compute_technician_workloads,
    evaluate_schedule_objective,
    is_strictly_better_objective,
    score_greedy_candidate,
)
from app.scheduler.optimizer import clone_routes, run_bounded_local_search
from app.scheduler.prioritization import (
    build_job_priority_profile,
    compute_soft_sla_urgency,
    compute_technician_scarcity_pressure,
    sort_jobs_by_policy,
)
from app.scheduler.travel import TravelMatrix
from app.schemas.scheduling import (
    AssignmentExplanation,
    Electrician,
    ExistingAssignment,
    Job,
    JobStatus,
    OptimizationChangeRecord,
    OptimizationSummary,
    ScheduledAssignment,
    ScheduleRunResult,
    SchedulerConfig,
    ScheduleSnapshot,
    TravelEntry,
    UnassignedJobReport,
    UnavailabilityInterval,
    minutes_to_hhmm,
    minutes_to_utc_datetime,
)

logger = logging.getLogger(__name__)


def _build_snapshot(
    stage: str,
    routes_by_tech: dict[str, list[RouteStop]],
    electricians: list[Electrician],
    elecs_by_id: dict[str, Electrician],
    active_jobs_by_id: dict[str, ResolvedJob],
    invalid_job_reports: dict[str, UnassignedJobReport],
    isolated_evals: dict[str, CandidateEvaluationResult],
    greedy_evals: dict[str, CandidateEvaluationResult],
    unavailability_by_tech: dict[str, list[UnavailabilityInterval]],
    existing_assignments: list[ExistingAssignment],
    baseline_assignments: dict[str, tuple[str, int]] | None,
    travel_matrix: TravelMatrix,
    config: SchedulerConfig,
    opt_changes: dict[str, OptimizationChangeRecord] | None = None,
) -> ScheduleSnapshot:
    """Materialize a complete ScheduleSnapshot with verified hard constraints and metrics."""
    validation = validate_full_schedule(
        routes_by_tech=routes_by_tech,
        electricians_by_id=elecs_by_id,
        valid_jobs_by_id=active_jobs_by_id,
        unavailability_by_tech=unavailability_by_tech,
        existing_assignments=existing_assignments,
        travel_matrix=travel_matrix,
        config=config,
    )
    objective = evaluate_schedule_objective(
        routes_by_tech=routes_by_tech,
        electricians=electricians,
        active_jobs_by_id=active_jobs_by_id,
        validation=validation,
        config=config,
        baseline_assignments=baseline_assignments,
    )
    workloads = compute_technician_workloads(electricians, routes_by_tech)

    scheduled_assignments: list[ScheduledAssignment] = []
    assigned_job_ids: list[str] = []
    urgencies: list[float] = []

    for tid in sorted(routes_by_tech.keys()):
        route = routes_by_tech[tid]
        elec = elecs_by_id[tid]
        for pos, stop in enumerate(route):
            skip_travel: int | None = None
            if pos + 1 < len(route):
                skip_res = travel_matrix.lookup(stop.from_location_id, route[pos + 1].job.location_id)
                skip_travel = skip_res.travel_time_min if skip_res is not None else None
            inc_travel = compute_incremental_travel_for_stop(route, pos, skip_travel)

            change_rec = opt_changes.get(stop.job.job_id) if opt_changes else None
            expl = build_assignment_explanation(
                stop=stop,
                route_position=pos,
                route_length=len(route),
                incremental_travel_min=inc_travel,
                electrician=elec,
                greedy_eval=greedy_evals.get(stop.job.job_id),
                config=config,
                opt_change=change_rec,
            )
            urg = compute_soft_sla_urgency(stop.slack_min, config.urgency_horizon_min)
            urgencies.append(urg)
            assigned_job_ids.append(stop.job.job_id)

            scheduled_assignments.append(
                ScheduledAssignment(
                    job_id=stop.job.job_id,
                    technician_id=tid,
                    priority=stop.job.priority,
                    route_position=pos,
                    from_location_id=stop.from_location_id,
                    departure_min=stop.departure_min,
                    arrival_min=stop.arrival_min,
                    planned_start_min=stop.planned_start_min,
                    completion_min=stop.completion_min,
                    departure_hhmm=minutes_to_hhmm(stop.departure_min),
                    arrival_hhmm=minutes_to_hhmm(stop.arrival_min),
                    planned_start_hhmm=minutes_to_hhmm(stop.planned_start_min),
                    completion_hhmm=minutes_to_hhmm(stop.completion_min),
                    planned_start_utc=minutes_to_utc_datetime(stop.planned_start_min, config.service_date),
                    planned_arrival_utc=minutes_to_utc_datetime(stop.arrival_min, config.service_date),
                    planned_completion_utc=minutes_to_utc_datetime(stop.completion_min, config.service_date),
                    travel_time_min=stop.travel_time_min,
                    incremental_travel_min=inc_travel,
                    service_duration_min=stop.job.duration_min,
                    sla_deadline_min=stop.job.sla_deadline_min,
                    slack_min=stop.slack_min,
                    soft_sla_urgency=urg,
                    is_hard_deadline=stop.job.is_hard_deadline,
                    travel_estimate_source=stop.travel_source,
                    status=stop.status,
                    is_protected=stop.is_protected,
                    changed_by_optimizer=change_rec is not None,
                    explanation=expl,
                )
            )

    assigned_set = set(assigned_job_ids)
    unassigned_reports: list[UnassignedJobReport] = []

    for jid in sorted(active_jobs_by_id.keys()):
        if jid in assigned_set:
            continue
        rjob = active_jobs_by_id[jid]
        final_eval = generate_candidates_for_job(
            job=rjob,
            electricians=electricians,
            routes_by_tech=routes_by_tech,
            unavailability_by_tech=unavailability_by_tech,
            travel_matrix=travel_matrix,
            config=config,
        )
        iso_eval = isolated_evals[jid]
        unassigned_reports.append(
            build_unassigned_job_report(
                job=rjob,
                final_eval=final_eval,
                isolated_eval=iso_eval,
                all_electricians=electricians,
            )
        )

    for jid in sorted(invalid_job_reports.keys()):
        unassigned_reports.append(invalid_job_reports[jid])

    unassigned_reports.sort(key=lambda r: r.job_id)
    unassigned_ids = [r.job_id for r in unassigned_reports]

    high_prio_unassigned = sum(
        1
        for r in unassigned_reports
        if r.priority.strip().lower() in ("critical", "p1", "high", "p2")
    )

    mean_urg = round(sum(urgencies) / float(len(urgencies)), 4) if urgencies else 0.0
    max_urg = round(max(urgencies), 4) if urgencies else 0.0

    # If invalid jobs were submitted, propagate them into objective unassigned count consistently
    if invalid_job_reports:
        objective.unassigned_count += len(invalid_job_reports)

    return ScheduleSnapshot(
        stage="initial_greedy" if stage == "initial_greedy" else "final_optimized",
        assignments=scheduled_assignments,
        assigned_job_ids=sorted(assigned_job_ids),
        unassigned_job_ids=unassigned_ids,
        unassigned_reports=unassigned_reports,
        technician_workloads=workloads,
        total_travel_min=objective.raw_total_travel_min,
        total_service_min=objective.raw_total_service_min,
        hard_constraint_violation_count=validation.hard_violation_count,
        hard_sla_violation_count=validation.hard_sla_violation_count,
        predicted_soft_sla_breach_count=objective.predicted_soft_sla_breach_count,
        mean_soft_sla_urgency=mean_urg,
        max_soft_sla_urgency=max_urg,
        high_priority_unassigned_count=high_prio_unassigned,
        objective=objective,
        is_valid_for_commitment=validation.is_valid,
        validation_errors=validation.errors,
    )


def generate_schedule(
    jobs: list[Job],
    electricians: list[Electrician],
    travel_times: list[TravelEntry] | TravelMatrix,
    existing_assignments: list[ExistingAssignment] | None = None,
    unavailability: list[UnavailabilityInterval] | None = None,
    config: SchedulerConfig | None = None,
    run_id: str | None = None,
    active_scenario_ids: list[str] | None = None,
    include_dataset_audit: bool = False,
    dataset_bundle: LoadedDatasetBundle | None = None,
) -> ScheduleRunResult:
    """Execute deterministic greedy scheduling (Module B) + bounded local search (Module C)."""
    cfg = config or SchedulerConfig()
    effective_run_id = run_id or f"run-{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc)
    existing_list = list(existing_assignments or [])
    unavail_list = list(unavailability or [])
    warnings: list[str] = []

    elecs_sorted = sorted(electricians, key=lambda e: e.technician_id)
    elecs_by_id: dict[str, Electrician] = {}
    for e in elecs_sorted:
        if e.technician_id in elecs_by_id:
            warnings.append(f"Duplicate technician_id '{e.technician_id}' ignored.")
            continue
        elecs_by_id[e.technician_id] = e
    unique_elecs = [elecs_by_id[tid] for tid in sorted(elecs_by_id.keys())]

    # Build or adapt TravelMatrix
    if isinstance(travel_times, TravelMatrix):
        t_matrix = travel_times
    else:
        t_matrix = TravelMatrix(
            entries=travel_times,
            electricians=unique_elecs,
            jobs=jobs,
            allow_coordinate_fallback=cfg.allow_coordinate_travel_fallback,
        )
    if t_matrix.invalid_entries:
        for inv in t_matrix.invalid_entries[:10]:
            warnings.append(f"Ignored invalid travel entry: {inv}")

    unavail_by_tech: dict[str, list[UnavailabilityInterval]] = {}
    for u in unavail_list:
        unavail_by_tech.setdefault(u.technician_id, []).append(u)
    for tid in unavail_by_tech:
        unavail_by_tech[tid].sort(key=lambda x: (x.start_min, x.end_min, x.unavailability_id))

    # Step 1: Validate input jobs & filter cancelled jobs
    cancelled_job_ids: set[str] = {
        ex.job_id for ex in existing_list if ex.status.strip().lower() == JobStatus.CANCELLED.value
    }
    active_jobs_by_id: dict[str, ResolvedJob] = {}
    invalid_job_reports: dict[str, UnassignedJobReport] = {}

    for job in jobs:
        if job.job_id in active_jobs_by_id or job.job_id in invalid_job_reports or job.job_id in cancelled_job_ids:
            if job.status.strip().lower() == JobStatus.CANCELLED.value or job.job_id in cancelled_job_ids:
                cancelled_job_ids.add(job.job_id)
                continue
            warnings.append(f"Duplicate job_id '{job.job_id}' ignored after first occurrence.")
            continue

        if job.status.strip().lower() == JobStatus.CANCELLED.value:
            cancelled_job_ids.add(job.job_id)
            continue

        rjob, failures = validate_job_data(job, cfg)
        if rjob is None:
            invalid_job_reports[job.job_id] = build_invalid_job_report(
                job_id=job.job_id,
                priority=job.priority,
                failures=failures,
            )
            warnings.append(
                f"Job '{job.job_id}' rejected due to invalid data: {'; '.join(f.detail for f in failures)}"
            )
            continue

        active_jobs_by_id[job.job_id] = rjob

    # Step 2: Anchor protected commitments & valid baseline assignments
    routes_by_tech: dict[str, list[RouteStop]] = {e.technician_id: [] for e in unique_elecs}
    protected_by_tech: dict[str, list[ExistingAssignment]] = {}
    unlocked_by_tech: dict[str, list[ExistingAssignment]] = {}
    baseline_assignments_map: dict[str, tuple[str, int]] = {}
    placed_job_ids: set[str] = set()

    for ex in existing_list:
        if ex.job_id in cancelled_job_ids:
            continue
        st = ex.status.strip().lower()
        is_prot = ex.locked or st == JobStatus.COMPLETED.value or (
            cfg.protect_in_progress and st == JobStatus.IN_PROGRESS.value
        )
        if ex.job_id not in active_jobs_by_id:
            warnings.append(
                f"Existing assignment references unknown or invalid job '{ex.job_id}'."
            )
            continue
        if ex.technician_id not in elecs_by_id:
            warnings.append(
                f"Existing assignment for '{ex.job_id}' references unknown technician '{ex.technician_id}'."
            )
            if is_prot:
                # Never silently reassign a protected commitment whose technician is missing
                placed_job_ids.add(ex.job_id)
            continue

        if is_prot:
            protected_by_tech.setdefault(ex.technician_id, []).append(ex)
        else:
            unlocked_by_tech.setdefault(ex.technician_id, []).append(ex)
            baseline_assignments_map[ex.job_id] = (ex.technician_id, ex.planned_start_min)

    # First place all protected commitments on their technicians
    for tid, prot_list in sorted(protected_by_tech.items()):
        elec = elecs_by_id[tid]
        prot_sorted = sorted(prot_list, key=lambda x: (x.planned_start_min, x.job_id))
        specs: list[StopSpec] = []
        for idx_p, p in enumerate(prot_sorted):
            p_status = p.status.strip().lower()
            is_hist = is_historical_or_active_commitment(p_status, True, cfg)
            init_origin = (
                elec.effective_start_location_id
                if idx_p == 0
                else active_jobs_by_id[prot_sorted[idx_p - 1].job_id].location_id
            )
            specs.append(
                StopSpec(
                    job=active_jobs_by_id[p.job_id],
                    status=p_status,
                    is_protected=True,
                    locked_start_min=p.planned_start_min,
                    locked_departure_min=p.departure_min,
                    locked_arrival_min=p.arrival_min,
                    locked_completion_min=(
                        p.completion_min if p_status == JobStatus.COMPLETED.value else None
                    ),
                    locked_origin_id=None if is_hist else init_origin,
                )
            )
        timed_prot, err = build_timed_route(
            electrician=elec,
            specs=specs,
            unavailability=unavail_by_tech.get(tid, []),
            travel_matrix=t_matrix,
            config=cfg,
        )
        if timed_prot is not None:
            routes_by_tech[tid] = timed_prot
            for s in timed_prot:
                placed_job_ids.add(s.job.job_id)
        else:
            # Input protected commitment conflicts with a hard constraint: keep technician and
            # planned_start_min pinned without silent movement, and let validate_full_schedule
            # report every hard-constraint violation explicitly.
            err_tag = f" ({err.code.value})" if err is not None else ""
            warnings.append(
                f"Protected commitment conflict on {tid}{err_tag}: {err.detail if err else 'unknown error'}"
            )
            fallback_stops: list[RouteStop] = []
            for idx_p, p in enumerate(prot_sorted):
                rj = active_jobs_by_id[p.job_id]
                p_status = p.status.strip().lower()
                is_hist = is_historical_or_active_commitment(p_status, True, cfg)
                orig = (
                    elec.effective_start_location_id
                    if idx_p == 0
                    else fallback_stops[-1].job.location_id
                )
                tr = t_matrix.lookup(orig, rj.location_id)
                t_val = tr.travel_time_min if tr is not None else 0
                t_src = tr.source if tr is not None else "missing_travel_data"
                if p.departure_min is not None:
                    dep = p.departure_min
                elif idx_p == 0:
                    dep = p.planned_start_min - t_val
                else:
                    dep = max(fallback_stops[-1].completion_min, p.planned_start_min - t_val)
                arr = p.arrival_min if p.arrival_min is not None else (dep + t_val)
                if p_status == JobStatus.COMPLETED.value and p.completion_min is not None:
                    comp = p.completion_min
                    locked_comp: int | None = p.completion_min
                else:
                    comp = p.planned_start_min + rj.duration_min
                    locked_comp = None
                fallback_stops.append(
                    RouteStop(
                        job=rj,
                        technician_id=tid,
                        from_location_id=orig,
                        departure_min=dep,
                        arrival_min=arr,
                        planned_start_min=p.planned_start_min,
                        completion_min=comp,
                        travel_time_min=t_val,
                        travel_source=t_src,
                        status=p_status,
                        is_protected=True,
                        locked_departure_min=dep if is_hist else p.departure_min,
                        locked_arrival_min=arr if is_hist else p.arrival_min,
                        locked_completion_min=locked_comp,
                        locked_origin_id=orig if is_hist else orig,
                    )
                )
                placed_job_ids.add(rj.job_id)
            routes_by_tech[tid] = fallback_stops

    # Next, preserve unaffected unlocked existing commitments that still satisfy all hard constraints
    for tid, unl_list in sorted(unlocked_by_tech.items()):
        elec = elecs_by_id[tid]
        unl_sorted = sorted(unl_list, key=lambda x: (x.planned_start_min, x.job_id))
        for u_ex in unl_sorted:
            if u_ex.job_id in placed_job_ids:
                continue
            rjob = active_jobs_by_id[u_ex.job_id]
            cur_specs = [stop_to_spec(s) for s in routes_by_tech[tid]]
            min_ins_idx = first_mutable_route_position(routes_by_tech[tid], cfg)
            # Find position ordered by start time without disturbing completed/in-progress work
            ins_idx = min_ins_idx
            for idx_s, s in enumerate(routes_by_tech[tid]):
                if s.planned_start_min <= u_ex.planned_start_min:
                    ins_idx = max(min_ins_idx, idx_s + 1)
            trial_spec = StopSpec(
                job=rjob,
                status="assigned",
                is_protected=False,
                preferred_min_start=u_ex.planned_start_min,
            )
            timed_try, _ = build_timed_route(
                electrician=elec,
                specs=cur_specs[:ins_idx] + [trial_spec] + cur_specs[ins_idx:],
                unavailability=unavail_by_tech.get(tid, []),
                travel_matrix=t_matrix,
                config=cfg,
            )
            if timed_try is None:
                # Retry without preferred_min_start in case predecessor shifted slightly (e.g. D03)
                trial_spec_earliest = StopSpec(job=rjob, status="assigned", is_protected=False)
                timed_try, _ = build_timed_route(
                    electrician=elec,
                    specs=cur_specs[:ins_idx] + [trial_spec_earliest] + cur_specs[ins_idx:],
                    unavailability=unavail_by_tech.get(tid, []),
                    travel_matrix=t_matrix,
                    config=cfg,
                )
            if timed_try is not None:
                routes_by_tech[tid] = timed_try
                placed_job_ids.add(rjob.job_id)

    # Step 3: Precompute isolated feasibility on empty routes (with active unavailability)
    empty_routes: dict[str, list[RouteStop]] = {e.technician_id: [] for e in unique_elecs}
    isolated_evals: dict[str, CandidateEvaluationResult] = {}
    static_eligible_map: dict[str, list[str]] = {}
    for jid, rjob in sorted(active_jobs_by_id.items()):
        iso_ev = generate_candidates_for_job(
            job=rjob,
            electricians=unique_elecs,
            routes_by_tech=empty_routes,
            unavailability_by_tech=unavail_by_tech,
            travel_matrix=t_matrix,
            config=cfg,
        )
        isolated_evals[jid] = iso_ev
        static_eligible_map[jid] = iso_ev.static_eligible_ids

    # Step 4-6: Deterministic Greedy Construction ordered by Priority -> Urgency -> Scarcity -> Job ID
    greedy_evals: dict[str, CandidateEvaluationResult] = {}
    remaining_ids = [jid for jid in sorted(active_jobs_by_id.keys()) if jid not in placed_job_ids]

    # Partition strictly by priority rank (1..4)
    tiers: dict[int, list[str]] = {1: [], 2: [], 3: [], 4: []}
    for jid in remaining_ids:
        tiers[active_jobs_by_id[jid].priority.rank].append(jid)

    for rank in (1, 2, 3, 4):
        tier_pool = list(tiers[rank])
        if not tier_pool:
            continue

        if not cfg.dynamic_priority_reordering:
            # Compute static ordering once at start of tier
            tier_profiles = []
            for jid in tier_pool:
                rj = active_jobs_by_id[jid]
                ev = generate_candidates_for_job(
                    job=rj,
                    electricians=unique_elecs,
                    routes_by_tech=routes_by_tech,
                    unavailability_by_tech=unavail_by_tech,
                    travel_matrix=t_matrix,
                    config=cfg,
                    baseline_assignment=baseline_assignments_map.get(jid),
                )
                tier_profiles.append(
                    build_job_priority_profile(
                        job=rj,
                        eligible_electrician_count=len(ev.static_eligible_ids),
                        feasible_electrician_count=ev.feasible_electrician_count,
                        feasible_slot_count=ev.feasible_slot_count,
                        best_slack_min=ev.best_slack_min,
                        horizon_min=cfg.urgency_horizon_min,
                    )
                )
            ordered_tier_ids = [p.job_id for p in sort_jobs_by_policy(tier_profiles)]
            for jid in ordered_tier_ids:
                rj = active_jobs_by_id[jid]
                ev = generate_candidates_for_job(
                    job=rj,
                    electricians=unique_elecs,
                    routes_by_tech=routes_by_tech,
                    unavailability_by_tech=unavail_by_tech,
                    travel_matrix=t_matrix,
                    config=cfg,
                    baseline_assignment=baseline_assignments_map.get(jid),
                )
                greedy_evals[jid] = ev
                if ev.candidates:
                    unassigned_now = [
                        active_jobs_by_id[u_id]
                        for u_id in active_jobs_by_id
                        if u_id not in placed_job_ids and u_id != jid
                    ]
                    pressure = compute_technician_scarcity_pressure(unassigned_now, static_eligible_map)
                    best_c = min(
                        ev.candidates,
                        key=lambda c: score_greedy_candidate(
                            c,
                            cfg,
                            pressure,
                            ev.feasible_electrician_count,
                            baseline_assignments_map.get(jid),
                        ),
                    )
                    routes_by_tech[best_c.technician_id] = best_c.updated_route
                    placed_job_ids.add(jid)
            continue

        # Dynamic ordering within the priority tier
        while tier_pool:
            eval_cache: dict[str, CandidateEvaluationResult] = {}
            profiles = []
            for jid in tier_pool:
                rj = active_jobs_by_id[jid]
                ev = generate_candidates_for_job(
                    job=rj,
                    electricians=unique_elecs,
                    routes_by_tech=routes_by_tech,
                    unavailability_by_tech=unavail_by_tech,
                    travel_matrix=t_matrix,
                    config=cfg,
                    baseline_assignment=baseline_assignments_map.get(jid),
                )
                eval_cache[jid] = ev
                profiles.append(
                    build_job_priority_profile(
                        job=rj,
                        eligible_electrician_count=len(ev.static_eligible_ids),
                        feasible_electrician_count=ev.feasible_electrician_count,
                        feasible_slot_count=ev.feasible_slot_count,
                        best_slack_min=ev.best_slack_min,
                        horizon_min=cfg.urgency_horizon_min,
                    )
                )

            selected_profile = sort_jobs_by_policy(profiles)[0]
            chosen_jid = selected_profile.job_id
            tier_pool.remove(chosen_jid)
            chosen_job = active_jobs_by_id[chosen_jid]
            chosen_eval = eval_cache[chosen_jid]
            greedy_evals[chosen_jid] = chosen_eval

            if chosen_eval.candidates:
                unassigned_now = [
                    active_jobs_by_id[u_id]
                    for u_id in active_jobs_by_id
                    if u_id not in placed_job_ids and u_id != chosen_jid
                ]
                pressure = compute_technician_scarcity_pressure(unassigned_now, static_eligible_map)
                best_cand = min(
                    chosen_eval.candidates,
                    key=lambda c: score_greedy_candidate(
                        c,
                        cfg,
                        pressure,
                        chosen_eval.feasible_electrician_count,
                        baseline_assignments_map.get(chosen_jid),
                    ),
                )
                routes_by_tech[best_cand.technician_id] = best_cand.updated_route
                placed_job_ids.add(chosen_jid)
            elif baseline_assignments_map:
                # During recovery, if an urgent higher-priority job (e.g. Critical J101) is blocked
                # solely by a pre-placed unlocked LOWER-priority baseline job, preempt that single
                # lower-priority job and return it to its lower-priority tier for rescheduling.
                preempted = False
                for tid in chosen_eval.static_eligible_ids:
                    elec = elecs_by_id[tid]
                    cur_route = routes_by_tech[tid]
                    base_specs = [stop_to_spec(s) for s in cur_route]
                    for idx_b, b_stop in enumerate(cur_route):
                        if b_stop.is_protected or b_stop.job.priority.rank <= chosen_job.priority.rank:
                            continue
                        rem_specs = base_specs[:idx_b] + base_specs[idx_b + 1:]
                        new_spec = StopSpec(job=chosen_job, status="assigned", is_protected=False)
                        min_pos_ins = first_mutable_spec_position(rem_specs, cfg)
                        for pos_ins in range(min_pos_ins, len(rem_specs) + 1):
                            timed_p, _ = build_timed_route(
                                electrician=elec,
                                specs=rem_specs[:pos_ins] + [new_spec] + rem_specs[pos_ins:],
                                unavailability=unavail_by_tech.get(tid, []),
                                travel_matrix=t_matrix,
                                config=cfg,
                            )
                            if timed_p is not None:
                                routes_by_tech[tid] = timed_p
                                placed_job_ids.remove(b_stop.job.job_id)
                                placed_job_ids.add(chosen_jid)
                                tiers[b_stop.job.priority.rank].append(b_stop.job.job_id)
                                preempted = True
                                break
                        if preempted:
                            break
                    if preempted:
                        break

    # Populate greedy_evals for pre-anchored existing commitments for explanation completeness
    for route in routes_by_tech.values():
        for stop in route:
            if stop.job.job_id not in greedy_evals:
                elig_e, _ = get_static_eligible_electricians(stop.job, unique_elecs)
                ev_placeholder = CandidateEvaluationResult(
                    job=stop.job,
                    static_eligible_ids=[e.technician_id for e in elig_e],
                )
                greedy_evals[stop.job.job_id] = ev_placeholder

    initial_routes = clone_routes(routes_by_tech)
    initial_snapshot = _build_snapshot(
        stage="initial_greedy",
        routes_by_tech=initial_routes,
        electricians=unique_elecs,
        elecs_by_id=elecs_by_id,
        active_jobs_by_id=active_jobs_by_id,
        invalid_job_reports=invalid_job_reports,
        isolated_evals=isolated_evals,
        greedy_evals=greedy_evals,
        unavailability_by_tech=unavail_by_tech,
        existing_assignments=existing_list,
        baseline_assignments=baseline_assignments_map or None,
        travel_matrix=t_matrix,
        config=cfg,
        opt_changes=None,
    )

    # Step 7: Module C Bounded Local Search
    opt_outcome = run_bounded_local_search(
        initial_routes=initial_routes,
        electricians=unique_elecs,
        active_jobs_by_id=active_jobs_by_id,
        unavailability_by_tech=unavail_by_tech,
        existing_assignments=existing_list,
        travel_matrix=t_matrix,
        config=cfg,
        baseline_assignments=baseline_assignments_map or None,
    )

    # Step 8: Full hard-constraint validation gate; never destroy a valid greedy schedule
    final_val = validate_full_schedule(
        routes_by_tech=opt_outcome.routes_by_tech,
        electricians_by_id=elecs_by_id,
        valid_jobs_by_id=active_jobs_by_id,
        unavailability_by_tech=unavail_by_tech,
        existing_assignments=existing_list,
        travel_matrix=t_matrix,
        config=cfg,
    )
    if not final_val.is_valid and initial_snapshot.is_valid_for_commitment:
        warnings.append(
            "Optimizer output failed full validation; safely preserved valid initial greedy schedule."
        )
        final_routes = clone_routes(initial_routes)
    else:
        final_routes = opt_outcome.routes_by_tech

    opt_changes = diff_schedules(initial_routes, final_routes)
    final_snapshot = _build_snapshot(
        stage="final_optimized",
        routes_by_tech=final_routes,
        electricians=unique_elecs,
        elecs_by_id=elecs_by_id,
        active_jobs_by_id=active_jobs_by_id,
        invalid_job_reports=invalid_job_reports,
        isolated_evals=isolated_evals,
        greedy_evals=greedy_evals,
        unavailability_by_tech=unavail_by_tech,
        existing_assignments=existing_list,
        baseline_assignments=baseline_assignments_map or None,
        travel_matrix=t_matrix,
        config=cfg,
        opt_changes=opt_changes,
    )

    if t_matrix.coordinate_fallback_pairs:
        sample_pairs = sorted(
            f"{u}->{v}" for u, v in t_matrix.coordinate_fallback_pairs
        )[:5]
        warnings.append(
            f"Used documented coordinate-detour travel estimate for {len(t_matrix.coordinate_fallback_pairs)} "
            f"location pair(s) absent from travel matrix (e.g. {', '.join(sample_pairs)})."
        )

    improved = is_strictly_better_objective(
        final_snapshot.objective,
        initial_snapshot.objective,
    )
    opt_summary = OptimizationSummary(
        enabled=cfg.enable_optimization,
        iterations_executed=opt_outcome.iterations_executed,
        moves_evaluated=opt_outcome.moves_evaluated,
        moves_accepted=opt_outcome.moves_accepted,
        runtime_seconds=opt_outcome.runtime_seconds,
        termination_reason=opt_outcome.termination_reason,
        improved=improved,
        initial_assigned_count=len(initial_snapshot.assigned_job_ids),
        final_assigned_count=len(final_snapshot.assigned_job_ids),
        assigned_count_delta=len(final_snapshot.assigned_job_ids) - len(initial_snapshot.assigned_job_ids),
        initial_travel_min=initial_snapshot.total_travel_min,
        final_travel_min=final_snapshot.total_travel_min,
        travel_min_delta=final_snapshot.total_travel_min - initial_snapshot.total_travel_min,
        initial_weighted_cost=initial_snapshot.objective.weighted_cost,
        final_weighted_cost=final_snapshot.objective.weighted_cost,
        weighted_cost_delta=round(
            final_snapshot.objective.weighted_cost - initial_snapshot.objective.weighted_cost, 8
        ),
        initial_mean_soft_sla_urgency=initial_snapshot.mean_soft_sla_urgency,
        final_mean_soft_sla_urgency=final_snapshot.mean_soft_sla_urgency,
        changes=[opt_changes[k] for k in sorted(opt_changes.keys())],
    )

    explanations_map: dict[str, AssignmentExplanation] = {
        a.job_id: a.explanation
        for a in final_snapshot.assignments
        if a.explanation is not None
    }
    unassigned_map: dict[str, UnassignedJobReport] = {
        r.job_id: r for r in final_snapshot.unassigned_reports
    }

    audit_report = None
    if include_dataset_audit:
        reason_counts = dict(
            Counter(r.primary_reason_code.value for r in final_snapshot.unassigned_reports)
        )
        if dataset_bundle is not None:
            audit_report = generate_dataset_audit(
                bundle=dataset_bundle,
                post_schedule_assigned_count=len(final_snapshot.assigned_job_ids),
                post_schedule_unassigned_count=len(final_snapshot.unassigned_job_ids),
                post_schedule_unassigned_by_reason=reason_counts,
            )
        elif not isinstance(travel_times, TravelMatrix):
            adhoc_bundle = LoadedDatasetBundle(
                data_dir=Path("."),
                electricians=unique_elecs,
                jobs=jobs,
                travel_entries=travel_times,
                unavailability=unavail_list,
            )
            audit_report = generate_dataset_audit(
                bundle=adhoc_bundle,
                post_schedule_assigned_count=len(final_snapshot.assigned_job_ids),
                post_schedule_unassigned_count=len(final_snapshot.unassigned_job_ids),
                post_schedule_unassigned_by_reason=reason_counts,
            )

    logger.info(
        "Schedule run %s completed: greedy=%d assigned (%d min travel) -> final=%d assigned (%d min travel), valid=%s",
        effective_run_id,
        len(initial_snapshot.assigned_job_ids),
        initial_snapshot.total_travel_min,
        len(final_snapshot.assigned_job_ids),
        final_snapshot.total_travel_min,
        final_snapshot.is_valid_for_commitment,
    )

    return ScheduleRunResult(
        run_id=effective_run_id,
        created_at_utc=created_at,
        active_scenario_ids=list(active_scenario_ids or []),
        config=cfg,
        initial_greedy_schedule=initial_snapshot,
        final_schedule=final_snapshot,
        optimization=opt_summary,
        assigned_job_ids=final_snapshot.assigned_job_ids,
        unassigned_job_ids=final_snapshot.unassigned_job_ids,
        explanations=explanations_map,
        unassigned_reasons=unassigned_map,
        validation_warnings=warnings,
        is_valid_for_commitment=final_snapshot.is_valid_for_commitment,
        dataset_audit=audit_report,
    )
