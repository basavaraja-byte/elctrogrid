"""Module C: Bounded deterministic local-search optimizer (Section 10).

Move neighborhoods explored deterministically:
1. Reinsert unassigned job (direct route insertion + 1-step relocate-blocking ejection).
2. Intra-route reordering (re-sequencing unlocked stops within a technician's route).
3. Inter-route relocation (moving an unlocked job to another eligible technician/slot).
4. Inter-route swap (exchanging two unlocked jobs between two eligible technicians).

Guarantees:
- Deterministic execution order and tie-breaking.
- Strict adherence to configured iteration and wall-clock runtime budgets.
- Explicit visited-state signature set preventing cycles.
- Protected commitments (completed, in_progress, locked) are never moved or altered.
- Zero hard-constraint violations accepted at any iteration.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.scheduler.candidates import (
    StopSpec,
    build_timed_route,
    first_mutable_route_position,
    first_mutable_spec_position,
    stop_to_spec,
)
from app.scheduler.constraints import (
    FullScheduleValidationResult,
    ResolvedJob,
    RouteStop,
    check_static_eligibility,
    validate_full_schedule,
)
from app.scheduler.objective import (
    evaluate_schedule_objective,
    is_strictly_better_objective,
    lexicographic_objective_key,
)
from app.scheduler.travel import TravelMatrix
from app.schemas.scheduling import (
    Electrician,
    ExistingAssignment,
    ObjectiveBreakdown,
    SchedulerConfig,
    TerminationReason,
    UnavailabilityInterval,
)


ScheduleSignature = tuple[tuple[str, tuple[tuple[str, int], ...]], ...]


@dataclass(slots=True)
class LocalSearchOutcome:
    """Result returned by Module C bounded local search."""

    routes_by_tech: dict[str, list[RouteStop]]
    final_objective: ObjectiveBreakdown
    iterations_executed: int
    moves_evaluated: int
    moves_accepted: int
    runtime_seconds: float
    termination_reason: TerminationReason


def clone_routes(routes_by_tech: dict[str, list[RouteStop]]) -> dict[str, list[RouteStop]]:
    """Deep-copy route lists and RouteStop instances."""
    return {tid: [s.clone() for s in route] for tid, route in routes_by_tech.items()}


def compute_schedule_signature(routes_by_tech: dict[str, list[RouteStop]]) -> ScheduleSignature:
    """Create an immutable canonical signature of all technician routes to prevent cycling."""
    return tuple(
        (tid, tuple((s.job.job_id, s.planned_start_min) for s in routes_by_tech[tid]))
        for tid in sorted(routes_by_tech.keys())
    )


def run_bounded_local_search(
    initial_routes: dict[str, list[RouteStop]],
    electricians: list[Electrician],
    active_jobs_by_id: dict[str, ResolvedJob],
    unavailability_by_tech: dict[str, list[UnavailabilityInterval]],
    existing_assignments: list[ExistingAssignment],
    travel_matrix: TravelMatrix,
    config: SchedulerConfig,
    baseline_assignments: dict[str, tuple[str, int]] | None = None,
) -> LocalSearchOutcome:
    """Improve an initial valid schedule via deterministic bounded local search."""
    start_clock = time.perf_counter()
    current_routes = clone_routes(initial_routes)
    elecs_sorted = sorted(electricians, key=lambda e: e.technician_id)
    elecs_by_id = {e.technician_id: e for e in elecs_sorted}

    init_val = validate_full_schedule(
        routes_by_tech=current_routes,
        electricians_by_id=elecs_by_id,
        valid_jobs_by_id=active_jobs_by_id,
        unavailability_by_tech=unavailability_by_tech,
        existing_assignments=existing_assignments,
        travel_matrix=travel_matrix,
        config=config,
    )
    current_obj = evaluate_schedule_objective(
        routes_by_tech=current_routes,
        electricians=elecs_sorted,
        active_jobs_by_id=active_jobs_by_id,
        validation=init_val,
        config=config,
        baseline_assignments=baseline_assignments,
    )

    if not config.enable_optimization or config.max_iterations == 0:
        return LocalSearchOutcome(
            routes_by_tech=current_routes,
            final_objective=current_obj,
            iterations_executed=0,
            moves_evaluated=0,
            moves_accepted=0,
            runtime_seconds=round(time.perf_counter() - start_clock, 6),
            termination_reason=TerminationReason.OPTIMIZATION_DISABLED,
        )

    # Precompute static eligibility lookup: job_id -> sorted list of eligible Electricians
    eligible_elecs_for_job: dict[str, list[Electrician]] = {}
    for jid, rjob in sorted(active_jobs_by_id.items()):
        eligible_elecs_for_job[jid] = [
            e for e in elecs_sorted if not check_static_eligibility(rjob, e)
        ]

    has_any_unlocked = any(
        not s.is_protected for route in current_routes.values() for s in route
    )
    assigned_ids_now = {s.job.job_id for r in current_routes.values() for s in r}
    has_unassigned = len(assigned_ids_now) < len(active_jobs_by_id)
    if not has_any_unlocked and not has_unassigned:
        return LocalSearchOutcome(
            routes_by_tech=current_routes,
            final_objective=current_obj,
            iterations_executed=0,
            moves_evaluated=0,
            moves_accepted=0,
            runtime_seconds=round(time.perf_counter() - start_clock, 6),
            termination_reason=TerminationReason.NO_MOVABLE_ASSIGNMENTS,
        )

    visited_signatures: set[ScheduleSignature] = {compute_schedule_signature(current_routes)}
    iterations = 0
    moves_evaluated = 0
    moves_accepted = 0
    budget_exceeded = False
    cycle_blocked = False

    def time_budget_exhausted() -> bool:
        return (time.perf_counter() - start_clock) >= config.max_runtime_seconds

    valid_gate_placeholder = FullScheduleValidationResult(is_valid=True)

    def evaluate_candidate_routes(
        modified_legs: dict[str, list[RouteStop]],
        incumbent_best: ObjectiveBreakdown,
    ) -> tuple[dict[str, list[RouteStop]], ObjectiveBreakdown] | None:
        nonlocal moves_evaluated, cycle_blocked
        moves_evaluated += 1

        if not init_val.is_valid:
            return None

        trial_routes = dict(current_routes)
        trial_routes.update(modified_legs)

        sig = compute_schedule_signature(trial_routes)
        if sig in visited_signatures:
            cycle_blocked = True
            return None

        # Modified routes are already validated by build_timed_route; compute objective first,
        # then run full schedule-wide validator before accepting any improving candidate.
        prelim_obj = evaluate_schedule_objective(
            routes_by_tech=trial_routes,
            electricians=elecs_sorted,
            active_jobs_by_id=active_jobs_by_id,
            validation=valid_gate_placeholder,
            config=config,
            baseline_assignments=baseline_assignments,
        )
        if not is_strictly_better_objective(prelim_obj, incumbent_best):
            return None

        val = validate_full_schedule(
            routes_by_tech=trial_routes,
            electricians_by_id=elecs_by_id,
            valid_jobs_by_id=active_jobs_by_id,
            unavailability_by_tech=unavailability_by_tech,
            existing_assignments=existing_assignments,
            travel_matrix=travel_matrix,
            config=config,
        )
        if not val.is_valid:
            return None

        return trial_routes, prelim_obj

    while iterations < config.max_iterations:
        if time_budget_exhausted():
            budget_exceeded = True
            break

        iterations += 1
        cycle_blocked = False
        best_step_routes: dict[str, list[RouteStop]] | None = None
        best_step_obj: ObjectiveBreakdown = current_obj

        assigned_set = {s.job.job_id for r in current_routes.values() for s in r}
        unassigned_jobs = sorted(
            (active_jobs_by_id[jid] for jid in active_jobs_by_id if jid not in assigned_set),
            key=lambda j: (j.priority.rank, j.sla_deadline_min, j.job_id),
        )

        # -------------------------------------------------------------------
        # Neighborhood 1: Reinsert unassigned job (direct + 1-step ejection)
        # -------------------------------------------------------------------
        found_coverage_gain = False
        for ujob in unassigned_jobs:
            if time_budget_exhausted():
                budget_exceeded = True
                break
            u_spec = StopSpec(job=ujob, status="assigned", is_protected=False)
            for elec in eligible_elecs_for_job.get(ujob.job_id, []):
                tid = elec.technician_id
                base_route = current_routes[tid]
                base_specs = [stop_to_spec(s) for s in base_route]
                unavail = unavailability_by_tech.get(tid, [])
                min_pos = first_mutable_route_position(base_route, config)

                # 1a. Direct insertion
                for pos in range(min_pos, len(base_specs) + 1):
                    timed, _ = build_timed_route(
                        electrician=elec,
                        specs=base_specs[:pos] + [u_spec] + base_specs[pos:],
                        unavailability=unavail,
                        travel_matrix=travel_matrix,
                        config=config,
                    )
                    if timed is None:
                        continue
                    cand_eval = evaluate_candidate_routes({tid: timed}, best_step_obj)
                    if cand_eval is not None:
                        best_step_routes, best_step_obj = cand_eval
                        found_coverage_gain = True

                # 1b. Ejection-relocation: relocate one unlocked stop on tid to alt_elec, insert ujob on tid
                for blk_idx, blk_stop in enumerate(base_route):
                    if time_budget_exhausted():
                        budget_exceeded = True
                        break
                    if blk_stop.is_protected:
                        continue
                    reduced_specs = base_specs[:blk_idx] + base_specs[blk_idx + 1:]
                    min_ins_pos = first_mutable_spec_position(reduced_specs, config)
                    for ins_pos in range(min_ins_pos, len(reduced_specs) + 1):
                        timed_primary, _ = build_timed_route(
                            electrician=elec,
                            specs=reduced_specs[:ins_pos] + [u_spec] + reduced_specs[ins_pos:],
                            unavailability=unavail,
                            travel_matrix=travel_matrix,
                            config=config,
                        )
                        if timed_primary is None:
                            continue

                        blk_spec = stop_to_spec(blk_stop)
                        for alt_elec in eligible_elecs_for_job.get(blk_stop.job.job_id, []):
                            alt_tid = alt_elec.technician_id
                            if alt_tid == tid:
                                continue
                            alt_specs = [stop_to_spec(s) for s in current_routes[alt_tid]]
                            alt_unavail = unavailability_by_tech.get(alt_tid, [])
                            min_alt_pos = first_mutable_route_position(current_routes[alt_tid], config)
                            for alt_pos in range(min_alt_pos, len(alt_specs) + 1):
                                timed_alt, _ = build_timed_route(
                                    electrician=alt_elec,
                                    specs=alt_specs[:alt_pos] + [blk_spec] + alt_specs[alt_pos:],
                                    unavailability=alt_unavail,
                                    travel_matrix=travel_matrix,
                                    config=config,
                                )
                                if timed_alt is None:
                                    continue
                                cand_eval = evaluate_candidate_routes(
                                    {tid: timed_primary, alt_tid: timed_alt},
                                    best_step_obj,
                                )
                                if cand_eval is not None:
                                    best_step_routes, best_step_obj = cand_eval
                                    found_coverage_gain = True
                                    break
                            if found_coverage_gain:
                                break
                        if found_coverage_gain:
                            break
                if found_coverage_gain or budget_exceeded:
                    break
            if found_coverage_gain or budget_exceeded:
                break

        # If we increased job coverage, commit immediately and start next iteration
        if found_coverage_gain and best_step_routes is not None:
            current_routes = clone_routes(best_step_routes)
            current_obj = best_step_obj
            visited_signatures.add(compute_schedule_signature(current_routes))
            moves_accepted += 1
            continue

        if budget_exceeded:
            break

        # -------------------------------------------------------------------
        # Neighborhood 2: Intra-route reordering
        # -------------------------------------------------------------------
        for elec in elecs_sorted:
            if time_budget_exhausted():
                budget_exceeded = True
                break
            tid = elec.technician_id
            route = current_routes[tid]
            if len(route) < 2:
                continue
            specs = [stop_to_spec(s) for s in route]
            unavail = unavailability_by_tech.get(tid, [])

            for i in range(len(specs)):
                if specs[i].is_protected:
                    continue
                moving_spec = specs[i]
                rem = specs[:i] + specs[i + 1:]
                min_j = first_mutable_spec_position(rem, config)
                for j in range(min_j, len(rem) + 1):
                    if j == i:
                        continue
                    reordered = rem[:j] + [moving_spec] + rem[j:]
                    timed, _ = build_timed_route(
                        electrician=elec,
                        specs=reordered,
                        unavailability=unavail,
                        travel_matrix=travel_matrix,
                        config=config,
                    )
                    if timed is None:
                        continue
                    cand_eval = evaluate_candidate_routes({tid: timed}, best_step_obj)
                    if cand_eval is not None:
                        best_step_routes, best_step_obj = cand_eval

        if budget_exceeded:
            break

        # -------------------------------------------------------------------
        # Neighborhood 3: Inter-route relocation (move unlocked job to another tech/slot)
        # -------------------------------------------------------------------
        for src_elec in elecs_sorted:
            if time_budget_exhausted():
                budget_exceeded = True
                break
            src_tid = src_elec.technician_id
            src_route = current_routes[src_tid]
            if not src_route:
                continue
            src_specs = [stop_to_spec(s) for s in src_route]
            src_unavail = unavailability_by_tech.get(src_tid, [])

            for idx, stop in enumerate(src_route):
                if stop.is_protected:
                    continue
                rem_src_specs = src_specs[:idx] + src_specs[idx + 1:]
                if rem_src_specs:
                    timed_src, _ = build_timed_route(
                        electrician=src_elec,
                        specs=rem_src_specs,
                        unavailability=src_unavail,
                        travel_matrix=travel_matrix,
                        config=config,
                    )
                    if timed_src is None:
                        continue
                else:
                    timed_src = []

                moving_spec = stop_to_spec(stop)
                for dst_elec in eligible_elecs_for_job.get(stop.job.job_id, []):
                    dst_tid = dst_elec.technician_id
                    if dst_tid == src_tid:
                        continue
                    dst_specs = [stop_to_spec(s) for s in current_routes[dst_tid]]
                    dst_unavail = unavailability_by_tech.get(dst_tid, [])
                    min_dst_pos = first_mutable_route_position(current_routes[dst_tid], config)
                    for dst_pos in range(min_dst_pos, len(dst_specs) + 1):
                        timed_dst, _ = build_timed_route(
                            electrician=dst_elec,
                            specs=dst_specs[:dst_pos] + [moving_spec] + dst_specs[dst_pos:],
                            unavailability=dst_unavail,
                            travel_matrix=travel_matrix,
                            config=config,
                        )
                        if timed_dst is None:
                            continue
                        cand_eval = evaluate_candidate_routes(
                            {src_tid: timed_src, dst_tid: timed_dst},
                            best_step_obj,
                        )
                        if cand_eval is not None:
                            best_step_routes, best_step_obj = cand_eval

        if budget_exceeded:
            break

        # -------------------------------------------------------------------
        # Neighborhood 4: Inter-route swap between two electricians
        # -------------------------------------------------------------------
        for idx_a in range(len(elecs_sorted)):
            if time_budget_exhausted():
                budget_exceeded = True
                break
            elec_a = elecs_sorted[idx_a]
            tid_a = elec_a.technician_id
            route_a = current_routes[tid_a]
            if not route_a:
                continue
            specs_a = [stop_to_spec(s) for s in route_a]
            unavail_a = unavailability_by_tech.get(tid_a, [])

            for idx_b in range(idx_a + 1, len(elecs_sorted)):
                if time_budget_exhausted():
                    budget_exceeded = True
                    break
                elec_b = elecs_sorted[idx_b]
                tid_b = elec_b.technician_id
                route_b = current_routes[tid_b]
                if not route_b:
                    continue
                specs_b = [stop_to_spec(s) for s in route_b]
                unavail_b = unavailability_by_tech.get(tid_b, [])

                for pos_a, stop_a in enumerate(route_a):
                    if stop_a.is_protected:
                        continue
                    if check_static_eligibility(stop_a.job, elec_b):
                        continue

                    for pos_b, stop_b in enumerate(route_b):
                        if stop_b.is_protected:
                            continue
                        if check_static_eligibility(stop_b.job, elec_a):
                            continue

                        # Swap directly at (pos_a, pos_b) and also test best valid position
                        spec_a = stop_to_spec(stop_a)
                        spec_b = stop_to_spec(stop_b)
                        rem_a = specs_a[:pos_a] + specs_a[pos_a + 1:]
                        rem_b = specs_b[:pos_b] + specs_b[pos_b + 1:]

                        best_a_route: list[RouteStop] | None = None
                        best_a_travel: int = 10**9
                        min_ins_a = first_mutable_spec_position(rem_a, config)
                        for ins_a in range(min_ins_a, len(rem_a) + 1):
                            ta, _ = build_timed_route(
                                electrician=elec_a,
                                specs=rem_a[:ins_a] + [spec_b] + rem_a[ins_a:],
                                unavailability=unavail_a,
                                travel_matrix=travel_matrix,
                                config=config,
                            )
                            if ta is not None:
                                tr_a = sum(s.travel_time_min for s in ta)
                                if tr_a < best_a_travel:
                                    best_a_travel = tr_a
                                    best_a_route = ta

                        if best_a_route is None:
                            continue

                        best_b_route: list[RouteStop] | None = None
                        best_b_travel: int = 10**9
                        min_ins_b = first_mutable_spec_position(rem_b, config)
                        for ins_b in range(min_ins_b, len(rem_b) + 1):
                            tb, _ = build_timed_route(
                                electrician=elec_b,
                                specs=rem_b[:ins_b] + [spec_a] + rem_b[ins_b:],
                                unavailability=unavail_b,
                                travel_matrix=travel_matrix,
                                config=config,
                            )
                            if tb is not None:
                                tr_b = sum(s.travel_time_min for s in tb)
                                if tr_b < best_b_travel:
                                    best_b_travel = tr_b
                                    best_b_route = tb

                        if best_b_route is None:
                            continue

                        cand_eval = evaluate_candidate_routes(
                            {tid_a: best_a_route, tid_b: best_b_route},
                            best_step_obj,
                        )
                        if cand_eval is not None:
                            best_step_routes, best_step_obj = cand_eval

        if best_step_routes is not None and lexicographic_objective_key(best_step_obj) < lexicographic_objective_key(current_obj):
            current_routes = clone_routes(best_step_routes)
            current_obj = best_step_obj
            visited_signatures.add(compute_schedule_signature(current_routes))
            moves_accepted += 1
        else:
            # No strictly improving move exists across any neighborhood
            if budget_exceeded:
                term = TerminationReason.MAX_RUNTIME_REACHED
            elif cycle_blocked and moves_evaluated > 0 and moves_accepted > 0 and best_step_routes is None:
                term = TerminationReason.LOCAL_OPTIMUM_REACHED
            else:
                term = TerminationReason.LOCAL_OPTIMUM_REACHED
            return LocalSearchOutcome(
                routes_by_tech=current_routes,
                final_objective=current_obj,
                iterations_executed=iterations,
                moves_evaluated=moves_evaluated,
                moves_accepted=moves_accepted,
                runtime_seconds=round(time.perf_counter() - start_clock, 6),
                termination_reason=term,
            )

    term_reason = (
        TerminationReason.MAX_RUNTIME_REACHED
        if budget_exceeded
        else TerminationReason.MAX_ITERATIONS_REACHED
    )
    return LocalSearchOutcome(
        routes_by_tech=current_routes,
        final_objective=current_obj,
        iterations_executed=iterations,
        moves_evaluated=moves_evaluated,
        moves_accepted=moves_accepted,
        runtime_seconds=round(time.perf_counter() - start_clock, 6),
        termination_reason=term_reason,
    )
