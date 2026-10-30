"""Candidate generation and exact route timing propagation for DispatchGrid."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from app.scheduler.constraints import (
    ConstraintFailure,
    ResolvedJob,
    RouteStop,
    check_static_eligibility,
    intervals_overlap,
    is_historical_or_active_commitment,
    shift_end_limit_for,
    validate_route,
)
from app.scheduler.prioritization import compute_soft_sla_urgency
from app.scheduler.travel import TravelMatrix
from app.schemas.scheduling import (
    Electrician,
    JobStatus,
    ReasonCode,
    SchedulerConfig,
    UnavailabilityInterval,
)


@dataclass(frozen=True, slots=True)
class StopSpec:
    """Input specification for placing a job into a route sequence."""

    job: ResolvedJob
    status: str = "assigned"
    is_protected: bool = False
    locked_start_min: int | None = None
    locked_departure_min: int | None = None
    locked_arrival_min: int | None = None
    locked_completion_min: int | None = None
    locked_origin_id: str | None = None
    preferred_min_start: int | None = None


@dataclass(slots=True)
class InsertionCandidate:
    """Feasible route-insertion candidate for a single job."""

    job: ResolvedJob
    technician_id: str
    insert_position: int
    stop: RouteStop
    updated_route: list[RouteStop]
    direct_leg_travel_min: int
    incremental_travel_min: int
    slack_min: int
    soft_sla_urgency: float
    new_service_minutes: int
    new_travel_minutes: int
    new_service_utilization: float


@dataclass(slots=True)
class CandidateEvaluationResult:
    """Complete result of static and dynamic candidate generation for one job."""

    job: ResolvedJob
    static_eligible_ids: list[str] = field(default_factory=list)
    candidates: list[InsertionCandidate] = field(default_factory=list)
    rejection_counts: Counter[str] = field(default_factory=Counter)
    rejection_details: list[ConstraintFailure] = field(default_factory=list)

    @property
    def feasible_electrician_count(self) -> int:
        return len({c.technician_id for c in self.candidates})

    @property
    def feasible_slot_count(self) -> int:
        return len(self.candidates)

    @property
    def best_slack_min(self) -> int | None:
        if not self.candidates:
            return None
        return max(c.slack_min for c in self.candidates)


def stop_to_spec(stop: RouteStop) -> StopSpec:
    """Convert an existing RouteStop back into a StopSpec for route reconstruction."""
    return StopSpec(
        job=stop.job,
        status=stop.status,
        is_protected=stop.is_protected,
        locked_start_min=stop.planned_start_min if stop.is_protected else None,
        locked_departure_min=stop.locked_departure_min if stop.is_protected else None,
        locked_arrival_min=stop.locked_arrival_min if stop.is_protected else None,
        locked_completion_min=stop.locked_completion_min if stop.is_protected else None,
        locked_origin_id=stop.locked_origin_id if stop.is_protected else None,
    )


def first_mutable_route_position(route: list[RouteStop], config: SchedulerConfig) -> int:
    """Return earliest index at which a future stop may be inserted without disturbing completed/active work."""
    last_hist_or_active = -1
    for idx, stop in enumerate(route):
        if is_historical_or_active_commitment(stop.status, stop.is_protected, config):
            last_hist_or_active = idx
    return last_hist_or_active + 1


def first_mutable_spec_position(specs: list[StopSpec], config: SchedulerConfig) -> int:
    """Return earliest index in StopSpecs after all historical ('completed') and active ('in_progress') stops."""
    last_hist_or_active = -1
    for idx, spec in enumerate(specs):
        if is_historical_or_active_commitment(spec.status, spec.is_protected, config):
            last_hist_or_active = idx
    return last_hist_or_active + 1


def build_timed_route(
    electrician: Electrician,
    specs: list[StopSpec],
    unavailability: list[UnavailabilityInterval],
    travel_matrix: TravelMatrix,
    config: SchedulerConfig,
) -> tuple[list[RouteStop] | None, ConstraintFailure | None]:
    """Propagate earliest feasible timing across an ordered list of StopSpecs.

    Returns (timed_route, None) if every stop in the sequence satisfies all hard
    constraints; otherwise returns (None, primary_failure).
    """
    if electrician.shift_end_min <= electrician.shift_start_min:
        return None, ConstraintFailure(
            ReasonCode.SHIFT_CONSTRAINT,
            f"Electrician {electrician.technician_id} shift_end ({electrician.shift_end_min}) <= shift_start ({electrician.shift_start_min}).",
        )

    sorted_unavail = sorted(unavailability, key=lambda u: (u.start_min, u.end_min))
    max_shift_end = shift_end_limit_for(electrician, config)
    timed_stops: list[RouteStop] = []

    for idx, spec in enumerate(specs):
        job = spec.job
        exempt_hist = is_historical_or_active_commitment(
            spec.status,
            spec.is_protected,
            config,
        )
        static_errs = check_static_eligibility(
            job,
            electrician,
            ignore_inactive_for_protected=exempt_hist,
        )
        if static_errs:
            return None, static_errs[0]

        origin = (
            electrician.effective_start_location_id
            if idx == 0
            else timed_stops[idx - 1].job.location_id
        )
        travel_res = travel_matrix.lookup(origin, job.location_id)
        if travel_res is None:
            return None, ConstraintFailure(
                ReasonCode.MISSING_TRAVEL_DATA,
                f"No travel data from '{origin}' to '{job.location_id}'.",
            )

        t_min = travel_res.travel_time_min
        if (
            not exempt_hist
            and electrician.max_travel_per_leg_min is not None
            and t_min > electrician.max_travel_per_leg_min
        ):
            return None, ConstraintFailure(
                ReasonCode.TRAVEL_CONFLICT,
                f"Travel time {t_min}m from {origin} to {job.location_id} exceeds max leg limit {electrician.max_travel_per_leg_min}m.",
            )

        ready_min = (
            electrician.shift_start_min
            if idx == 0
            else timed_stops[idx - 1].completion_min
        )

        if spec.is_protected and spec.locked_start_min is not None:
            planned_start = spec.locked_start_min

            if exempt_hist:
                # Preserve historical/active timing fields without recalculation when recorded
                if spec.locked_departure_min is not None:
                    departure = spec.locked_departure_min
                elif idx == 0:
                    departure = planned_start - t_min
                else:
                    departure = max(ready_min, planned_start - t_min)

                arrival = (
                    spec.locked_arrival_min
                    if spec.locked_arrival_min is not None
                    else departure + t_min
                )
                if (
                    spec.status.strip().lower() == JobStatus.COMPLETED.value
                    and spec.locked_completion_min is not None
                ):
                    completion = spec.locked_completion_min
                    stored_locked_comp: int | None = spec.locked_completion_min
                else:
                    completion = planned_start + job.duration_min
                    stored_locked_comp = None

                stored_locked_dep: int | None = departure
                stored_locked_arr: int | None = arrival
                stored_locked_orig: str | None = origin
            else:
                # Locked future assignment: preserve technician and planned_start_min,
                # preserve explicit departure/arrival when predecessor origin is unchanged,
                # and enforce all applicable future hard constraints.
                same_origin = spec.locked_origin_id is None or spec.locked_origin_id == origin
                if same_origin and spec.locked_departure_min is not None:
                    departure = spec.locked_departure_min
                elif idx == 0:
                    departure = planned_start - t_min
                else:
                    departure = max(ready_min, planned_start - t_min)

                arrival = (
                    spec.locked_arrival_min
                    if (same_origin and spec.locked_arrival_min is not None)
                    else departure + t_min
                )
                completion = planned_start + job.duration_min
                stored_locked_dep = spec.locked_departure_min
                stored_locked_arr = spec.locked_arrival_min
                stored_locked_comp = None
                stored_locked_orig = spec.locked_origin_id

            if idx > 0 and departure < timed_stops[idx - 1].completion_min:
                return None, ConstraintFailure(
                    ReasonCode.TRAVEL_CONFLICT,
                    f"Protected commitment {job.job_id} departure ({departure}) overlaps predecessor "
                    f"{timed_stops[idx - 1].job.job_id} completion ({timed_stops[idx - 1].completion_min}).",
                )

            if arrival < departure + t_min:
                return None, ConstraintFailure(
                    ReasonCode.TRAVEL_CONFLICT,
                    f"Protected commitment {job.job_id} arrival ({arrival}) < departure + travel ({departure + t_min}).",
                )

            if not exempt_hist and (
                departure < electrician.shift_start_min
                or planned_start < electrician.shift_start_min
            ):
                return None, ConstraintFailure(
                    ReasonCode.SHIFT_CONSTRAINT,
                    f"Locked future assignment {job.job_id} departure ({departure}) or start ({planned_start}) "
                    f"precedes shift_start_min ({electrician.shift_start_min}) on {electrician.technician_id}.",
                )

            if arrival > planned_start:
                return None, ConstraintFailure(
                    ReasonCode.TRAVEL_CONFLICT,
                    f"Cannot reach protected commitment {job.job_id} by locked start {planned_start} "
                    f"(earliest arrival {arrival} from {origin}).",
                )

            if not exempt_hist:
                if completion > max_shift_end:
                    return None, ConstraintFailure(
                        ReasonCode.SHIFT_CONSTRAINT,
                        f"Locked future assignment {job.job_id} on {electrician.technician_id} finishes at {completion} > shift limit {max_shift_end}.",
                    )
                if planned_start < job.window_start_min:
                    return None, ConstraintFailure(
                        ReasonCode.NO_AVAILABLE_SLOT,
                        f"Locked future assignment {job.job_id} start {planned_start} precedes window_start_min {job.window_start_min}.",
                    )
                if planned_start > job.window_end_min:
                    return None, ConstraintFailure(
                        ReasonCode.NO_AVAILABLE_SLOT,
                        f"Locked future assignment {job.job_id} start {planned_start} exceeds window_end_min {job.window_end_min}.",
                    )
                for u in sorted_unavail:
                    if intervals_overlap(departure, completion, u.start_min, u.end_min):
                        return None, ConstraintFailure(
                            ReasonCode.NO_AVAILABLE_SLOT,
                            f"Locked future assignment {job.job_id} [{departure}, {completion}) overlaps unavailability "
                            f"{u.unavailability_id} [{u.start_min}, {u.end_min}) ({u.reason}).",
                        )
                if job.is_hard_deadline and completion > job.sla_deadline_min:
                    return None, ConstraintFailure(
                        ReasonCode.SLA_DEADLINE_INFEASIBLE,
                        f"Locked future assignment {job.job_id} completion {completion} misses hard SLA deadline {job.sla_deadline_min}.",
                    )

            timed_stops.append(
                RouteStop(
                    job=job,
                    technician_id=electrician.technician_id,
                    from_location_id=origin,
                    departure_min=departure,
                    arrival_min=arrival,
                    planned_start_min=planned_start,
                    completion_min=completion,
                    travel_time_min=t_min,
                    travel_source=travel_res.source,
                    status=spec.status,
                    is_protected=True,
                    locked_departure_min=stored_locked_dep,
                    locked_arrival_min=stored_locked_arr,
                    locked_completion_min=stored_locked_comp,
                    locked_origin_id=stored_locked_orig,
                )
            )
            continue

        # Schedulable (unlocked) stop: compute earliest valid departure & start
        target_earliest_start = job.window_start_min
        if spec.preferred_min_start is not None:
            target_earliest_start = max(target_earliest_start, spec.preferred_min_start)

        departure = max(ready_min, electrician.shift_start_min, target_earliest_start - t_min)

        # Advance past any overlapping unavailability intervals
        pushed_by_unavailability = False
        while True:
            completion_try = departure + t_min + job.duration_min
            overlapping_u: UnavailabilityInterval | None = None
            for u in sorted_unavail:
                if intervals_overlap(departure, completion_try, u.start_min, u.end_min):
                    overlapping_u = u
                    break
            if overlapping_u is None:
                break
            pushed_by_unavailability = True
            departure = max(overlapping_u.end_min, target_earliest_start - t_min)

        arrival = departure + t_min
        planned_start = max(arrival, target_earliest_start)
        completion = planned_start + job.duration_min

        # Check hard upper bounds in clear diagnostic priority order
        if completion > max_shift_end:
            return None, ConstraintFailure(
                ReasonCode.SHIFT_CONSTRAINT,
                f"Job {job.job_id} on {electrician.technician_id} finishes at {completion} > shift limit {max_shift_end}.",
            )

        if planned_start > job.window_end_min:
            # Distinguish travel conflict vs unavailability/route capacity vs shift start
            if idx > 0 and timed_stops[idx - 1].completion_min <= job.window_end_min < timed_stops[idx - 1].completion_min + t_min:
                return None, ConstraintFailure(
                    ReasonCode.TRAVEL_CONFLICT,
                    f"Insufficient travel time ({t_min}m) from {origin} (finishing {timed_stops[idx - 1].completion_min}) "
                    f"to start {job.job_id} by window_end {job.window_end_min}.",
                )
            if idx == 0 and not pushed_by_unavailability and electrician.shift_start_min + t_min > job.window_end_min:
                return None, ConstraintFailure(
                    ReasonCode.TRAVEL_CONFLICT,
                    f"Shift start ({electrician.shift_start_min}) + travel ({t_min}m) exceeds {job.job_id} window_end ({job.window_end_min}).",
                )
            code = ReasonCode.RESOURCE_CAPACITY_EXHAUSTED if (idx > 0 and not pushed_by_unavailability) else ReasonCode.NO_AVAILABLE_SLOT
            return None, ConstraintFailure(
                code,
                f"Earliest available start {planned_start} on {electrician.technician_id} exceeds window_end {job.window_end_min}.",
            )

        if job.is_hard_deadline and completion > job.sla_deadline_min:
            return None, ConstraintFailure(
                ReasonCode.SLA_DEADLINE_INFEASIBLE,
                f"Earliest completion {completion} on {electrician.technician_id} misses hard SLA deadline {job.sla_deadline_min}.",
            )

        timed_stops.append(
            RouteStop(
                job=job,
                technician_id=electrician.technician_id,
                from_location_id=origin,
                departure_min=departure,
                arrival_min=arrival,
                planned_start_min=planned_start,
                completion_min=completion,
                travel_time_min=t_min,
                travel_source=travel_res.source,
                status=spec.status,
                is_protected=False,
            )
        )

    # Final defensive verification of the entire route against Module B validator
    route_errs = validate_route(
        electrician=electrician,
        route=timed_stops,
        unavailability=sorted_unavail,
        travel_matrix=travel_matrix,
        config=config,
    )
    if route_errs:
        return None, route_errs[0]

    return timed_stops, None


def get_static_eligible_electricians(
    job: ResolvedJob,
    electricians: list[Electrician],
) -> tuple[list[Electrician], list[ConstraintFailure]]:
    """Return statically eligible active electricians and any static rejection diagnostics."""
    eligible: list[Electrician] = []
    failures: list[ConstraintFailure] = []
    for elec in electricians:
        errs = check_static_eligibility(job, elec)
        if not errs:
            eligible.append(elec)
        else:
            failures.extend(errs)
    return eligible, failures


def generate_candidates_for_job(
    job: ResolvedJob,
    electricians: list[Electrician],
    routes_by_tech: dict[str, list[RouteStop]],
    unavailability_by_tech: dict[str, list[UnavailabilityInterval]],
    travel_matrix: TravelMatrix,
    config: SchedulerConfig,
    baseline_assignment: tuple[str, int] | None = None,
) -> CandidateEvaluationResult:
    """Generate all feasible route-insertion candidates for a job across all electricians.

    Accounts for both predecessor and successor travel legs and full downstream
    timing revalidation whenever inserting into an existing route.
    """
    eval_res = CandidateEvaluationResult(job=job)
    eligible_elecs, static_failures = get_static_eligible_electricians(job, electricians)
    eval_res.static_eligible_ids = [e.technician_id for e in eligible_elecs]

    if not eligible_elecs:
        for f in static_failures:
            eval_res.rejection_counts[f.code.value] += 1
        eval_res.rejection_details.extend(static_failures)
        return eval_res

    for elec in eligible_elecs:
        tid = elec.technician_id
        current_route = routes_by_tech.get(tid, [])
        old_travel = sum(s.travel_time_min for s in current_route)
        base_specs = [stop_to_spec(s) for s in current_route]
        unavail = unavailability_by_tech.get(tid, [])
        shift_len = max(1, elec.shift_end_min - elec.shift_start_min)
        min_pos = first_mutable_route_position(current_route, config)

        for pos in range(min_pos, len(base_specs) + 1):
            preferred_starts: list[int | None] = [None]
            if baseline_assignment is not None and baseline_assignment[0] == tid:
                preferred_starts.append(baseline_assignment[1])

            seen_starts_at_pos: set[int] = set()
            for pref_start in preferred_starts:
                new_spec = StopSpec(
                    job=job,
                    status="assigned",
                    is_protected=False,
                    preferred_min_start=pref_start,
                )
                trial_specs = base_specs[:pos] + [new_spec] + base_specs[pos:]
                timed_route, err = build_timed_route(
                    electrician=elec,
                    specs=trial_specs,
                    unavailability=unavail,
                    travel_matrix=travel_matrix,
                    config=config,
                )
                if timed_route is None:
                    if pref_start is None and err is not None:
                        # Distinguish whether failure was due to existing commitments on route
                        if (
                            current_route
                            and err.code in (ReasonCode.NO_AVAILABLE_SLOT, ReasonCode.SHIFT_CONSTRAINT, ReasonCode.SLA_DEADLINE_INFEASIBLE)
                        ):
                            # Check if job would fit on an empty route for this electrician
                            empty_route, _ = build_timed_route(
                                electrician=elec,
                                specs=[new_spec],
                                unavailability=unavail,
                                travel_matrix=travel_matrix,
                                config=config,
                            )
                            if empty_route is not None:
                                err = ConstraintFailure(
                                    ReasonCode.RESOURCE_CAPACITY_EXHAUSTED,
                                    f"Electrician {tid} is eligible in isolation, but existing route commitments prevent inserting {job.job_id} at position {pos} ({err.detail}).",
                                )
                        eval_res.rejection_counts[err.code.value] += 1
                        eval_res.rejection_details.append(err)
                    continue

                inserted_stop = timed_route[pos]
                if inserted_stop.planned_start_min in seen_starts_at_pos:
                    continue
                seen_starts_at_pos.add(inserted_stop.planned_start_min)

                new_travel = sum(s.travel_time_min for s in timed_route)
                new_service = sum(s.job.duration_min for s in timed_route)
                inc_travel = new_travel - old_travel
                slack = inserted_stop.slack_min
                urgency = compute_soft_sla_urgency(slack, config.urgency_horizon_min)

                eval_res.candidates.append(
                    InsertionCandidate(
                        job=job,
                        technician_id=tid,
                        insert_position=pos,
                        stop=inserted_stop,
                        updated_route=timed_route,
                        direct_leg_travel_min=inserted_stop.travel_time_min,
                        incremental_travel_min=inc_travel,
                        slack_min=slack,
                        soft_sla_urgency=urgency,
                        new_service_minutes=new_service,
                        new_travel_minutes=new_travel,
                        new_service_utilization=new_service / float(shift_len),
                    )
                )

    return eval_res

