"""Module B: Hard-Constraint Validation for DispatchGrid.

Hard constraints are strictly separated from cost scoring. Any candidate or schedule
violating an applicable hard constraint is rejected before objective evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.scheduler.travel import TravelMatrix
from app.schemas.scheduling import (
    Electrician,
    ExistingAssignment,
    Job,
    JobStatus,
    PriorityLevel,
    ReasonCode,
    SchedulerConfig,
    UnavailabilityInterval,
    normalize_priority,
)


@dataclass(frozen=True, slots=True)
class ConstraintFailure:
    """Structured record of a single hard-constraint violation."""

    code: ReasonCode
    detail: str


@dataclass(frozen=True, slots=True)
class ResolvedJob:
    """Validated and normalized job ready for constraint & candidate evaluation."""

    job_id: str
    trade: str
    job_type: str
    required_skills: tuple[str, ...]
    required_certifications: tuple[str, ...]
    priority: PriorityLevel
    duration_min: int
    zone: str
    location_id: str
    location_x_km: float | None
    location_y_km: float | None
    window_start_min: int
    window_end_min: int
    sla_deadline_min: int
    is_hard_deadline: bool
    status: str
    notes: str


@dataclass(slots=True)
class RouteStop:
    """Internal mutable/immutable representation of a stop along a technician route."""

    job: ResolvedJob
    technician_id: str
    from_location_id: str
    departure_min: int
    arrival_min: int
    planned_start_min: int
    completion_min: int
    travel_time_min: int
    travel_source: str = "matrix_lookup"
    status: str = "assigned"
    is_protected: bool = False
    locked_departure_min: int | None = None
    locked_arrival_min: int | None = None
    locked_completion_min: int | None = None
    locked_origin_id: str | None = None

    @property
    def slack_min(self) -> int:
        return self.job.sla_deadline_min - self.completion_min

    def clone(self) -> RouteStop:
        return RouteStop(
            job=self.job,
            technician_id=self.technician_id,
            from_location_id=self.from_location_id,
            departure_min=self.departure_min,
            arrival_min=self.arrival_min,
            planned_start_min=self.planned_start_min,
            completion_min=self.completion_min,
            travel_time_min=self.travel_time_min,
            travel_source=self.travel_source,
            status=self.status,
            is_protected=self.is_protected,
            locked_departure_min=self.locked_departure_min,
            locked_arrival_min=self.locked_arrival_min,
            locked_completion_min=self.locked_completion_min,
            locked_origin_id=self.locked_origin_id,
        )


@dataclass(slots=True)
class FullScheduleValidationResult:
    """Result of full-schedule hard-constraint verification before commitment."""

    is_valid: bool
    hard_violation_count: int = 0
    protected_violation_count: int = 0
    hard_sla_violation_count: int = 0
    errors: list[str] = field(default_factory=list)


def is_job_hard_deadline(job: Job, priority: PriorityLevel, config: SchedulerConfig) -> bool:
    """Determine whether a job's SLA completion deadline is hard under current policy."""
    if job.is_hard_deadline is not None:
        return job.is_hard_deadline
    if config.sla_mode == "hard":
        return True
    if config.sla_mode == "hard_critical_only":
        return priority == PriorityLevel.CRITICAL
    return False


def validate_job_data(
    job: Job,
    config: SchedulerConfig,
) -> tuple[ResolvedJob | None, list[ConstraintFailure]]:
    """Validate intrinsic job fields, durations, priorities, and timestamps."""
    failures: list[ConstraintFailure] = []

    if not job.trade or not job.trade.strip():
        failures.append(ConstraintFailure(ReasonCode.INVALID_JOB_DATA, "Job trade is empty."))

    if not job.zone or not job.zone.strip():
        failures.append(ConstraintFailure(ReasonCode.INVALID_JOB_DATA, "Job service zone is empty."))

    if job.duration_min <= 0:
        failures.append(
            ConstraintFailure(
                ReasonCode.INVALID_JOB_DATA,
                f"Job duration_min must be positive (got {job.duration_min}).",
            )
        )

    try:
        priority = normalize_priority(job.priority)
    except ValueError as exc:
        failures.append(ConstraintFailure(ReasonCode.INVALID_JOB_DATA, str(exc)))
        priority = PriorityLevel.NORMAL

    try:
        ws, we, sla = job.resolve_times(config.service_date)
    except ValueError as exc:
        failures.append(ConstraintFailure(ReasonCode.INVALID_JOB_DATA, str(exc)))
        return None, failures

    effective_ws = 0 if ws is None else ws
    effective_we = 1440 if we is None else we
    effective_sla = effective_we + max(0, job.duration_min) if sla is None else sla

    if effective_ws < 0:
        failures.append(
            ConstraintFailure(
                ReasonCode.INVALID_JOB_DATA,
                f"Earliest start window_start_min ({effective_ws}) cannot be negative.",
            )
        )
    if effective_we < 0:
        failures.append(
            ConstraintFailure(
                ReasonCode.INVALID_JOB_DATA,
                f"Latest start window_end_min ({effective_we}) cannot be negative.",
            )
        )
    if ws is not None and we is not None and effective_we < effective_ws:
        failures.append(
            ConstraintFailure(
                ReasonCode.INVALID_JOB_DATA,
                f"window_end_min ({effective_we}) precedes window_start_min ({effective_ws}).",
            )
        )
    if effective_sla < 0:
        failures.append(
            ConstraintFailure(
                ReasonCode.INVALID_JOB_DATA,
                f"sla_deadline_min ({effective_sla}) cannot be negative.",
            )
        )

    if failures:
        return None, failures

    hard_dl = is_job_hard_deadline(job, priority, config)
    return (
        ResolvedJob(
            job_id=job.job_id,
            trade=job.trade.strip(),
            job_type=job.job_type.strip(),
            required_skills=tuple(dict.fromkeys(job.required_skills)),
            required_certifications=tuple(dict.fromkeys(job.required_certifications)),
            priority=priority,
            duration_min=job.duration_min,
            zone=job.zone.strip(),
            location_id=job.effective_location_id,
            location_x_km=job.location_x_km,
            location_y_km=job.location_y_km,
            window_start_min=effective_ws,
            window_end_min=effective_we,
            sla_deadline_min=effective_sla,
            is_hard_deadline=hard_dl,
            status=job.status.strip().lower(),
            notes=job.notes,
        ),
        [],
    )


def check_static_eligibility(
    job: ResolvedJob,
    electrician: Electrician,
    *,
    ignore_inactive_for_protected: bool = False,
) -> list[ConstraintFailure]:
    """Validate trade, active status, required skills, mandatory certifications, and zone."""
    failures: list[ConstraintFailure] = []

    if not ignore_inactive_for_protected and not electrician.is_active:
        failures.append(
            ConstraintFailure(
                ReasonCode.NO_AVAILABLE_SLOT,
                f"Electrician {electrician.technician_id} has status '{electrician.status}' (not active).",
            )
        )

    if electrician.trade.strip().lower() != job.trade.lower():
        failures.append(
            ConstraintFailure(
                ReasonCode.MISSING_SKILL,
                f"Electrician {electrician.technician_id} trade '{electrician.trade}' != job trade '{job.trade}'.",
            )
        )

    elec_certs = set(electrician.certifications)
    missing_certs = [c for c in job.required_certifications if c not in elec_certs]
    if missing_certs:
        failures.append(
            ConstraintFailure(
                ReasonCode.MISSING_CERTIFICATION,
                f"Electrician {electrician.technician_id} lacks certification(s): {', '.join(missing_certs)}.",
            )
        )

    elec_skills = set(electrician.skills)
    missing_skills = [s for s in job.required_skills if s not in elec_skills]
    if missing_skills:
        failures.append(
            ConstraintFailure(
                ReasonCode.MISSING_SKILL,
                f"Electrician {electrician.technician_id} lacks skill(s): {', '.join(missing_skills)}.",
            )
        )

    if job.zone not in set(electrician.eligible_zones):
        failures.append(
            ConstraintFailure(
                ReasonCode.ZONE_INELIGIBLE,
                f"Electrician {electrician.technician_id} eligible zones {electrician.eligible_zones} exclude '{job.zone}'.",
            )
        )

    return failures


def shift_end_limit_for(electrician: Electrician, config: SchedulerConfig) -> int:
    """Compute maximum permissible route completion minute for a technician."""
    overtime_allowance = config.max_overtime_min if config.allow_overtime else 0
    return electrician.shift_end_min + overtime_allowance


def intervals_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Return True iff half-open intervals [a_start, a_end) and [b_start, b_end) overlap."""
    return a_start < b_end and a_end > b_start


def is_historical_or_active_commitment(
    status: str,
    is_protected: bool,
    config: SchedulerConfig,
) -> bool:
    """Return True only for already-executed ('completed') or protected active ('in_progress') work.

    Future commitments marked locked=True (e.g., status='assigned' or 'pending') remain
    protected against reassignment or start-time drift, but are NOT exempt from applicable
    hard constraints (active technician status, shift bounds, availability, time windows,
    max leg travel, and hard SLA deadlines).
    """
    if not is_protected:
        return False
    norm = status.strip().lower()
    if norm == JobStatus.COMPLETED.value:
        return True
    if norm == JobStatus.IN_PROGRESS.value and config.protect_in_progress:
        return True
    return False


def validate_stop_against_constraints(
    stop: RouteStop,
    electrician: Electrician,
    prev_stop: RouteStop | None,
    unavailability: list[UnavailabilityInterval],
    travel_matrix: TravelMatrix,
    config: SchedulerConfig,
) -> list[ConstraintFailure]:
    """Validate all hard constraints for a single stop given its predecessor on the route."""
    failures: list[ConstraintFailure] = []

    if electrician.shift_end_min <= electrician.shift_start_min:
        failures.append(
            ConstraintFailure(
                ReasonCode.SHIFT_CONSTRAINT,
                f"Electrician {electrician.technician_id} has invalid shift [{electrician.shift_start_min}, {electrician.shift_end_min}].",
            )
        )
        return failures

    if stop.job.duration_min <= 0:
        failures.append(
            ConstraintFailure(
                ReasonCode.INVALID_JOB_DATA,
                f"Stop {stop.job.job_id} has non-positive duration_min ({stop.job.duration_min}).",
            )
        )

    if stop.job.window_end_min < stop.job.window_start_min:
        failures.append(
            ConstraintFailure(
                ReasonCode.INVALID_JOB_DATA,
                f"Stop {stop.job.job_id} has inverted time window [{stop.job.window_start_min}, {stop.job.window_end_min}].",
            )
        )

    exempt_historical_or_active = is_historical_or_active_commitment(
        stop.status,
        stop.is_protected,
        config,
    )

    # 1. Static eligibility (preserve completed/in-progress even if tech later went off-duty;
    #    locked future assignments must still satisfy active technician eligibility)
    static_failures = check_static_eligibility(
        stop.job,
        electrician,
        ignore_inactive_for_protected=exempt_historical_or_active,
    )
    failures.extend(static_failures)

    # 2. Expected origin and travel verification
    expected_origin = (
        electrician.effective_start_location_id
        if prev_stop is None
        else prev_stop.job.location_id
    )
    if stop.from_location_id != expected_origin:
        failures.append(
            ConstraintFailure(
                ReasonCode.TRAVEL_CONFLICT,
                f"Stop {stop.job.job_id} origin '{stop.from_location_id}' != expected '{expected_origin}'.",
            )
        )

    travel_res = travel_matrix.lookup(expected_origin, stop.job.location_id)
    if travel_res is None:
        failures.append(
            ConstraintFailure(
                ReasonCode.MISSING_TRAVEL_DATA,
                f"Missing travel-time entry from '{expected_origin}' to '{stop.job.location_id}'.",
            )
        )
        return failures

    if stop.travel_time_min != travel_res.travel_time_min:
        failures.append(
            ConstraintFailure(
                ReasonCode.TRAVEL_CONFLICT,
                f"Stop {stop.job.job_id} travel_time_min ({stop.travel_time_min}) != resolved ({travel_res.travel_time_min}).",
            )
        )

    if (
        not exempt_historical_or_active
        and electrician.max_travel_per_leg_min is not None
        and travel_res.travel_time_min > electrician.max_travel_per_leg_min
    ):
        failures.append(
            ConstraintFailure(
                ReasonCode.TRAVEL_CONFLICT,
                f"Travel leg {expected_origin}->{stop.job.location_id} ({travel_res.travel_time_min}m) exceeds max_travel_per_leg_min ({electrician.max_travel_per_leg_min}m).",
            )
        )

    # 3. Shift start & predecessor sequencing (no overlap)
    if not exempt_historical_or_active and (
        stop.departure_min < electrician.shift_start_min
        or stop.planned_start_min < electrician.shift_start_min
    ):
        failures.append(
            ConstraintFailure(
                ReasonCode.SHIFT_CONSTRAINT,
                f"Stop {stop.job.job_id} departure ({stop.departure_min}) or start ({stop.planned_start_min}) "
                f"precedes shift_start_min ({electrician.shift_start_min}) on {electrician.technician_id}.",
            )
        )

    if prev_stop is not None and stop.departure_min < prev_stop.completion_min:
        failures.append(
            ConstraintFailure(
                ReasonCode.TRAVEL_CONFLICT,
                f"Stop {stop.job.job_id} departure ({stop.departure_min}) overlaps predecessor {prev_stop.job.job_id} completion ({prev_stop.completion_min}).",
            )
        )

    # 4. Internal stop timing equations
    expected_arrival = stop.departure_min + travel_res.travel_time_min
    if stop.arrival_min < expected_arrival:
        failures.append(
            ConstraintFailure(
                ReasonCode.TRAVEL_CONFLICT,
                f"Stop {stop.job.job_id} arrival ({stop.arrival_min}) < departure + travel ({expected_arrival}).",
            )
        )

    if stop.planned_start_min < stop.arrival_min:
        failures.append(
            ConstraintFailure(
                ReasonCode.TRAVEL_CONFLICT,
                f"Stop {stop.job.job_id} planned_start ({stop.planned_start_min}) < arrival ({stop.arrival_min}).",
            )
        )

    if (
        stop.status.strip().lower() == JobStatus.COMPLETED.value
        and stop.locked_completion_min is not None
    ):
        if stop.completion_min != stop.locked_completion_min or stop.completion_min < stop.planned_start_min:
            failures.append(
                ConstraintFailure(
                    ReasonCode.INVALID_JOB_DATA,
                    f"Completed stop {stop.job.job_id} completion ({stop.completion_min}) violates recorded historical completion ({stop.locked_completion_min}).",
                )
            )
    else:
        expected_completion = stop.planned_start_min + stop.job.duration_min
        if stop.completion_min != expected_completion:
            failures.append(
                ConstraintFailure(
                    ReasonCode.INVALID_JOB_DATA,
                    f"Stop {stop.job.job_id} completion ({stop.completion_min}) != start + duration ({expected_completion}).",
                )
            )

    # 5. For all future stops (both unlocked AND locked future assignments), enforce time windows,
    #    shift end, unavailability intervals, and hard SLA deadlines. Only historical ('completed')
    #    and protected active ('in_progress') commitments bypass post-hoc window/shift/SLA checks.
    if not exempt_historical_or_active:
        if stop.planned_start_min < stop.job.window_start_min:
            failures.append(
                ConstraintFailure(
                    ReasonCode.NO_AVAILABLE_SLOT,
                    f"Start {stop.planned_start_min} precedes window_start_min {stop.job.window_start_min}.",
                )
            )
        if stop.planned_start_min > stop.job.window_end_min:
            failures.append(
                ConstraintFailure(
                    ReasonCode.NO_AVAILABLE_SLOT,
                    f"Start {stop.planned_start_min} exceeds window_end_min {stop.job.window_end_min}.",
                )
            )

        max_end = shift_end_limit_for(electrician, config)
        if stop.completion_min > max_end:
            failures.append(
                ConstraintFailure(
                    ReasonCode.SHIFT_CONSTRAINT,
                    f"Completion {stop.completion_min} exceeds shift limit {max_end} on {electrician.technician_id}.",
                )
            )

        for u in unavailability:
            if intervals_overlap(stop.departure_min, stop.completion_min, u.start_min, u.end_min):
                failures.append(
                    ConstraintFailure(
                        ReasonCode.NO_AVAILABLE_SLOT,
                        f"Stop {stop.job.job_id} [{stop.departure_min}, {stop.completion_min}) overlaps unavailability "
                        f"{u.unavailability_id} [{u.start_min}, {u.end_min}) ({u.reason}).",
                    )
                )

        if stop.job.is_hard_deadline and stop.completion_min > stop.job.sla_deadline_min:
            failures.append(
                ConstraintFailure(
                    ReasonCode.SLA_DEADLINE_INFEASIBLE,
                    f"Completion {stop.completion_min} misses hard SLA deadline {stop.job.sla_deadline_min}.",
                )
            )

    return failures


def validate_route(
    electrician: Electrician,
    route: list[RouteStop],
    unavailability: list[UnavailabilityInterval],
    travel_matrix: TravelMatrix,
    config: SchedulerConfig,
) -> list[ConstraintFailure]:
    """Validate an entire ordered route for one electrician."""
    failures: list[ConstraintFailure] = []
    prev_stop: RouteStop | None = None
    for stop in route:
        if stop.technician_id != electrician.technician_id:
            failures.append(
                ConstraintFailure(
                    ReasonCode.INVALID_JOB_DATA,
                    f"Stop {stop.job.job_id} technician_id '{stop.technician_id}' != route owner '{electrician.technician_id}'.",
                )
            )
        stop_failures = validate_stop_against_constraints(
            stop=stop,
            electrician=electrician,
            prev_stop=prev_stop,
            unavailability=unavailability,
            travel_matrix=travel_matrix,
            config=config,
        )
        failures.extend(stop_failures)
        prev_stop = stop
    return failures


def validate_full_schedule(
    routes_by_tech: dict[str, list[RouteStop]],
    electricians_by_id: dict[str, Electrician],
    valid_jobs_by_id: dict[str, ResolvedJob],
    unavailability_by_tech: dict[str, list[UnavailabilityInterval]],
    existing_assignments: list[ExistingAssignment],
    travel_matrix: TravelMatrix,
    config: SchedulerConfig,
) -> FullScheduleValidationResult:
    """Comprehensive schedule-wide hard-constraint validator required prior to commitment."""
    result = FullScheduleValidationResult(is_valid=True)
    seen_jobs: dict[str, str] = {}
    stop_lookup: dict[str, RouteStop] = {}

    # 1. Validate each technician route and check duplicate/cancelled/unknown jobs
    for tech_id, route in sorted(routes_by_tech.items()):
        elec = electricians_by_id.get(tech_id)
        if elec is None:
            result.hard_violation_count += 1
            result.errors.append(f"Route exists for unknown technician '{tech_id}'.")
            continue

        route_failures = validate_route(
            electrician=elec,
            route=route,
            unavailability=unavailability_by_tech.get(tech_id, []),
            travel_matrix=travel_matrix,
            config=config,
        )
        for failure in route_failures:
            result.hard_violation_count += 1
            if failure.code == ReasonCode.SLA_DEADLINE_INFEASIBLE:
                result.hard_sla_violation_count += 1
            result.errors.append(f"[{tech_id}] {failure.code.value}: {failure.detail}")

        last_hist_or_active_idx = -1
        for idx_s, stop in enumerate(route):
            if is_historical_or_active_commitment(stop.status, stop.is_protected, config):
                last_hist_or_active_idx = idx_s

        for idx_s, stop in enumerate(route):
            jid = stop.job.job_id
            if (
                idx_s < last_hist_or_active_idx
                and not is_historical_or_active_commitment(stop.status, stop.is_protected, config)
            ):
                result.hard_violation_count += 1
                result.protected_violation_count += 1
                result.errors.append(
                    f"[{tech_id}] Future stop {jid} is sequenced ahead of completed/in-progress work."
                )

            if jid in seen_jobs:
                result.hard_violation_count += 1
                result.errors.append(
                    f"Duplicate assignment for job {jid} on {seen_jobs[jid]} and {tech_id}."
                )
            else:
                seen_jobs[jid] = tech_id
                stop_lookup[jid] = stop

            if jid not in valid_jobs_by_id:
                result.hard_violation_count += 1
                result.errors.append(f"Assigned job {jid} is not in validated active jobs.")
            elif valid_jobs_by_id[jid].status == JobStatus.CANCELLED.value:
                result.hard_violation_count += 1
                result.errors.append(f"Cancelled job {jid} must not remain scheduled.")

    # 2. Verify all protected commitments remain preserved without silent drift or unprotection
    for existing in existing_assignments:
        st = existing.status.strip().lower()
        if st == JobStatus.CANCELLED.value:
            continue
        is_prot = existing.locked or st == JobStatus.COMPLETED.value or (
            config.protect_in_progress and st == JobStatus.IN_PROGRESS.value
        )
        if not is_prot:
            continue
        if existing.job_id in valid_jobs_by_id and valid_jobs_by_id[existing.job_id].status == JobStatus.CANCELLED.value:
            continue

        actual = stop_lookup.get(existing.job_id)
        if actual is None:
            result.hard_violation_count += 1
            result.protected_violation_count += 1
            result.errors.append(
                f"Protected commitment {existing.job_id} ({existing.status}) was dropped from schedule."
            )
            continue

        if not actual.is_protected:
            result.hard_violation_count += 1
            result.protected_violation_count += 1
            result.errors.append(
                f"Protected commitment {existing.job_id} lost its is_protected invariant flag."
            )

        if actual.status.strip().lower() != st:
            result.hard_violation_count += 1
            result.protected_violation_count += 1
            result.errors.append(
                f"Protected commitment {existing.job_id} status changed from '{existing.status}' to '{actual.status}'."
            )

        if actual.technician_id != existing.technician_id:
            result.hard_violation_count += 1
            result.protected_violation_count += 1
            result.errors.append(
                f"Protected commitment {existing.job_id} moved from {existing.technician_id} to {actual.technician_id}."
            )

        if actual.planned_start_min != existing.planned_start_min:
            result.hard_violation_count += 1
            result.protected_violation_count += 1
            result.errors.append(
                f"Protected commitment {existing.job_id} start changed from {existing.planned_start_min} to {actual.planned_start_min}."
            )

        # Historical ('completed') and protected active ('in_progress') timing fields must not be recalculated
        if is_historical_or_active_commitment(st, True, config):
            if existing.departure_min is not None and actual.departure_min != existing.departure_min:
                result.hard_violation_count += 1
                result.protected_violation_count += 1
                result.errors.append(
                    f"Protected commitment {existing.job_id} ({existing.status}) departure_min changed "
                    f"from {existing.departure_min} to {actual.departure_min}."
                )
            if existing.arrival_min is not None and actual.arrival_min != existing.arrival_min:
                result.hard_violation_count += 1
                result.protected_violation_count += 1
                result.errors.append(
                    f"Protected commitment {existing.job_id} ({existing.status}) arrival_min changed "
                    f"from {existing.arrival_min} to {actual.arrival_min}."
                )
            if (
                st == JobStatus.COMPLETED.value
                and existing.completion_min is not None
                and actual.completion_min != existing.completion_min
            ):
                result.hard_violation_count += 1
                result.protected_violation_count += 1
                result.errors.append(
                    f"Completed commitment {existing.job_id} completion_min changed "
                    f"from {existing.completion_min} to {actual.completion_min}."
                )

    result.is_valid = result.hard_violation_count == 0 and result.protected_violation_count == 0
    return result
