"""Evidence-based explanations for assigned and unassigned jobs (Section 11)."""

from __future__ import annotations

from collections import Counter

from app.scheduler.candidates import CandidateEvaluationResult
from app.scheduler.constraints import (
    ConstraintFailure,
    ResolvedJob,
    RouteStop,
    check_static_eligibility,
    is_historical_or_active_commitment,
)
from app.scheduler.prioritization import classify_deadline_risk, compute_soft_sla_urgency
from app.schemas.scheduling import (
    AssignmentExplanation,
    Electrician,
    OptimizationChangeRecord,
    ReasonCode,
    SchedulerConfig,
    UnassignedJobReport,
    minutes_to_hhmm,
)


_STATIC_REASON_PRIORITY: list[ReasonCode] = [
    ReasonCode.INVALID_JOB_DATA,
    ReasonCode.MISSING_CERTIFICATION,
    ReasonCode.MISSING_SKILL,
    ReasonCode.ZONE_INELIGIBLE,
]

_DYNAMIC_REASON_PRIORITY: list[ReasonCode] = [
    ReasonCode.MISSING_TRAVEL_DATA,
    ReasonCode.RESOURCE_CAPACITY_EXHAUSTED,
    ReasonCode.SLA_DEADLINE_INFEASIBLE,
    ReasonCode.SHIFT_CONSTRAINT,
    ReasonCode.TRAVEL_CONFLICT,
    ReasonCode.NO_AVAILABLE_SLOT,
]


def compute_incremental_travel_for_stop(
    route: list[RouteStop],
    stop_index: int,
    direct_skip_travel_min: int | None,
) -> int:
    """Compute net route travel added by stop at stop_index (predecessor + successor - skipped leg)."""
    stop = route[stop_index]
    if stop_index + 1 >= len(route):
        return stop.travel_time_min
    next_stop = route[stop_index + 1]
    if direct_skip_travel_min is None:
        return stop.travel_time_min
    return stop.travel_time_min + next_stop.travel_time_min - direct_skip_travel_min


def build_assignment_explanation(
    stop: RouteStop,
    route_position: int,
    route_length: int,
    incremental_travel_min: int,
    electrician: Electrician,
    greedy_eval: CandidateEvaluationResult | None,
    config: SchedulerConfig,
    opt_change: OptimizationChangeRecord | None = None,
) -> AssignmentExplanation:
    """Construct a grounded explanation for an assigned RouteStop."""
    job = stop.job
    slack = stop.slack_min
    urgency = compute_soft_sla_urgency(slack, config.urgency_horizon_min)
    risk_label = classify_deadline_risk(slack, config.urgency_horizon_min)

    skills_str = ", ".join(job.required_skills) if job.required_skills else "general electrical"
    certs_Part = (
        f", certifications [{', '.join(job.required_certifications)}]"
        if job.required_certifications
        else ""
    )
    exempt_hist = is_historical_or_active_commitment(stop.status, stop.is_protected, config)
    static_errs = check_static_eligibility(
        job,
        electrician,
        ignore_inactive_for_protected=exempt_hist,
    )
    if static_errs:
        eligibility_reason = (
            f"Protected commitment pinned to {electrician.technician_id}, but static eligibility "
            f"conflicts exist: {'; '.join(e.detail for e in static_errs)}"
        )
    elif not electrician.is_active and exempt_hist:
        eligibility_reason = (
            f"Historical/active commitment ({stop.status}) preserved on {electrician.technician_id} "
            f"(current status '{electrician.status}') in trade '{electrician.trade}', zone '{job.zone}'."
        )
    else:
        eligibility_reason = (
            f"Electrician {electrician.technician_id} is active in trade '{electrician.trade}', "
            f"holds required skill(s) [{skills_str}]{certs_Part}, and serves zone '{job.zone}' "
            f"within shift {minutes_to_hhmm(electrician.shift_start_min)}-{minutes_to_hhmm(electrician.shift_end_min)}."
        )

    if route_length == 1:
        route_impact = (
            f"Only job on {electrician.technician_id}'s route; departs {stop.from_location_id} at "
            f"{minutes_to_hhmm(stop.departure_min)} ({stop.travel_time_min} min travel)."
        )
    elif route_position == route_length - 1:
        route_impact = (
            f"Appended as stop #{route_position + 1} of {route_length} after {stop.from_location_id} "
            f"(+{incremental_travel_min} min incremental route travel; leg travel {stop.travel_time_min} min)."
        )
    else:
        route_impact = (
            f"Inserted at stop #{route_position + 1} of {route_length} after {stop.from_location_id}; "
            f"net route travel delta {incremental_travel_min:+d} min (inbound leg {stop.travel_time_min} min)."
        )

    candidates_evaluated = 0
    candidates_feasible = 1
    rejected_summary: dict[str, int] = {}
    if greedy_eval is not None:
        rejected_summary = dict(greedy_eval.rejection_counts)
        candidates_feasible = len(greedy_eval.candidates)
        candidates_evaluated = candidates_feasible + sum(rejected_summary.values())

    if stop.is_protected:
        selection_reason = (
            f"Preserved protected commitment ({stop.status}) on {electrician.technician_id} "
            f"starting at {minutes_to_hhmm(stop.planned_start_min)}."
        )
    elif opt_change is not None:
        selection_reason = (
            f"Selected during bounded local search optimization ({opt_change.note})."
        )
    elif greedy_eval is not None and len(greedy_eval.static_eligible_ids) == 1:
        selection_reason = (
            f"{electrician.technician_id} is the sole statically eligible electrician for "
            f"skills [{skills_str}] in zone '{job.zone}'; best feasible slot starts at "
            f"{minutes_to_hhmm(stop.planned_start_min)} with {slack} min SLA slack."
        )
    else:
        selection_reason = (
            f"Best feasible candidate out of {candidates_feasible} feasible slot(s) across "
            f"{len(greedy_eval.static_eligible_ids) if greedy_eval else 1} eligible electrician(s): "
            f"incremental travel {incremental_travel_min} min, SLA slack {slack} min (urgency {urgency:.1f})."
        )

    return AssignmentExplanation(
        job_id=job.job_id,
        selected_technician_id=electrician.technician_id,
        planned_departure_min=stop.departure_min,
        planned_arrival_min=stop.arrival_min,
        planned_start_min=stop.planned_start_min,
        planned_completion_min=stop.completion_min,
        travel_time_min=stop.travel_time_min,
        incremental_travel_min=incremental_travel_min,
        route_position=route_position,
        from_location_id=stop.from_location_id,
        to_location_id=job.location_id,
        eligibility_reason=eligibility_reason,
        selection_reason=selection_reason,
        route_impact=route_impact,
        sla_deadline_min=job.sla_deadline_min,
        slack_min=slack,
        soft_sla_urgency=urgency,
        deadline_risk_label=risk_label,
        candidates_evaluated=candidates_evaluated,
        candidates_feasible=candidates_feasible,
        rejected_summary_by_reason=rejected_summary,
        changed_during_optimization=opt_change is not None,
        optimization_change_note=opt_change.note if opt_change is not None else None,
    )


def build_invalid_job_report(
    job_id: str,
    priority: str,
    failures: list[ConstraintFailure],
) -> UnassignedJobReport:
    """Create an UnassignedJobReport for a job failing intrinsic data validation."""
    details = [f.detail for f in failures]
    counts = Counter(f.code.value for f in failures)
    return UnassignedJobReport(
        job_id=job_id,
        priority=priority,
        primary_reason_code=ReasonCode.INVALID_JOB_DATA,
        summary=f"Job {job_id} has invalid input data: {'; '.join(details)}",
        is_statically_eligible=False,
        static_eligible_count=0,
        static_eligible_technician_ids=[],
        isolated_feasible_count=0,
        rejection_counts_by_code=dict(counts),
        supporting_details=details[:10],
    )


def build_unassigned_job_report(
    job: ResolvedJob,
    final_eval: CandidateEvaluationResult,
    isolated_eval: CandidateEvaluationResult,
    all_electricians: list[Electrician],
) -> UnassignedJobReport:
    """Create a grounded UnassignedJobReport distinguishing static vs dynamic infeasibility."""
    static_ids = final_eval.static_eligible_ids
    static_count = len(static_ids)
    isolated_count = isolated_eval.feasible_electrician_count
    counts = dict(final_eval.rejection_counts)

    # Case 1: Zero statically eligible electricians
    if static_count == 0:
        active_elecs = [e for e in all_electricians if e.is_active]
        if not active_elecs:
            return UnassignedJobReport(
                job_id=job.job_id,
                priority=job.priority.value,
                primary_reason_code=ReasonCode.NO_AVAILABLE_SLOT,
                summary=f"No active electricians are currently available to serve job {job.job_id}.",
                is_statically_eligible=False,
                static_eligible_count=0,
                static_eligible_technician_ids=[],
                isolated_feasible_count=0,
                rejection_counts_by_code=counts,
                supporting_details=[f.detail for f in final_eval.rejection_details[:8]],
            )

        # Inspect fleet-wide skill, certification, and zone coverage
        cert_matches = [
            e for e in active_elecs
            if set(job.required_certifications).issubset(set(e.certifications))
        ]
        skill_matches = [
            e for e in active_elecs
            if e.trade.strip().lower() == job.trade.lower()
            and set(job.required_skills).issubset(set(e.skills))
        ]
        zone_matches = [
            e for e in active_elecs
            if job.zone in set(e.eligible_zones)
        ]

        supporting: list[str] = []
        if job.required_certifications and not cert_matches:
            primary = ReasonCode.MISSING_CERTIFICATION
            supporting.append(
                f"Zero active electricians hold mandatory certification(s): {', '.join(job.required_certifications)}."
            )
        elif not skill_matches:
            primary = ReasonCode.MISSING_SKILL
            missing_across_fleet = [
                sk for sk in job.required_skills
                if not any(sk in e.skills for e in active_elecs)
            ]
            if missing_across_fleet:
                supporting.append(
                    f"Zero active electricians possess required skill/authorization: {', '.join(missing_across_fleet)}."
                )
            else:
                supporting.append(
                    f"No single active electrician simultaneously possesses all required skills: {', '.join(job.required_skills)}."
                )
        elif not zone_matches:
            primary = ReasonCode.ZONE_INELIGIBLE
        else:
            # Both skill-holders and zone-holders exist separately, but intersection is empty!
            primary = ReasonCode.ZONE_INELIGIBLE
            supporting.append(
                f"{len(skill_matches)} electrician(s) have skills [{', '.join(job.required_skills)}] "
                f"({', '.join(e.technician_id for e in skill_matches)}), and {len(zone_matches)} serve zone '{job.zone}', "
                f"but no active electrician satisfies both simultaneously."
            )

        if not zone_matches:
            supporting.append(
                f"Zero active electricians are eligible to work in zone '{job.zone}'."
            )
        if job.required_certifications and cert_matches and primary != ReasonCode.MISSING_CERTIFICATION:
            supporting.append(
                f"{len(cert_matches)} electrician(s) hold required certifications."
            )

        summary = (
            f"No eligible electrician in current roster for job {job.job_id}: "
            + " ".join(supporting)
        )
        return UnassignedJobReport(
            job_id=job.job_id,
            priority=job.priority.value,
            primary_reason_code=primary,
            summary=summary,
            is_statically_eligible=False,
            static_eligible_count=0,
            static_eligible_technician_ids=[],
            isolated_feasible_count=0,
            rejection_counts_by_code=counts,
            supporting_details=supporting + [f.detail for f in final_eval.rejection_details[:5]],
        )

    # Case 2: Statically eligible electricians exist, but 0 feasible slots even on empty shifts
    if isolated_count == 0:
        iso_counts = isolated_eval.rejection_counts
        primary = ReasonCode.NO_AVAILABLE_SLOT
        for candidate_code in [
            ReasonCode.MISSING_TRAVEL_DATA,
            ReasonCode.SLA_DEADLINE_INFEASIBLE,
            ReasonCode.SHIFT_CONSTRAINT,
            ReasonCode.TRAVEL_CONFLICT,
            ReasonCode.NO_AVAILABLE_SLOT,
        ]:
            if iso_counts.get(candidate_code.value, 0) > 0:
                primary = candidate_code
                break

        details = [f.detail for f in isolated_eval.rejection_details[:8]]
        summary = (
            f"{static_count} electrician(s) ({', '.join(static_ids)}) are statically qualified for {job.job_id}, "
            f"but zero feasible time slots exist even without competing jobs ({primary.value}): "
            f"{details[0] if details else 'time/shift/deadline bounds cannot be satisfied.'}"
        )
        return UnassignedJobReport(
            job_id=job.job_id,
            priority=job.priority.value,
            primary_reason_code=primary,
            summary=summary,
            is_statically_eligible=True,
            static_eligible_count=static_count,
            static_eligible_technician_ids=static_ids,
            isolated_feasible_count=0,
            rejection_counts_by_code=dict(iso_counts),
            supporting_details=details,
        )

    # Case 3: Statically AND individually feasible, but blocked by current schedule commitments
    primary = ReasonCode.RESOURCE_CAPACITY_EXHAUSTED
    if counts.get(ReasonCode.RESOURCE_CAPACITY_EXHAUSTED.value, 0) == 0:
        for code in _DYNAMIC_REASON_PRIORITY:
            if counts.get(code.value, 0) > 0:
                primary = code
                break

    details = [f.detail for f in final_eval.rejection_details[:8]]
    summary = (
        f"{static_count} electrician(s) ({', '.join(static_ids)}) are statically eligible and "
        f"{isolated_count} had feasible isolated slots, but all {sum(counts.values())} route-insertion "
        f"positions conflicted with higher-priority/existing commitments ({primary.value})."
    )
    return UnassignedJobReport(
        job_id=job.job_id,
        priority=job.priority.value,
        primary_reason_code=primary,
        summary=summary,
        is_statically_eligible=True,
        static_eligible_count=static_count,
        static_eligible_technician_ids=static_ids,
        isolated_feasible_count=isolated_count,
        rejection_counts_by_code=counts,
        supporting_details=details,
    )


def diff_schedules(
    initial_routes: dict[str, list[RouteStop]],
    final_routes: dict[str, list[RouteStop]],
) -> dict[str, OptimizationChangeRecord]:
    """Compare initial greedy routes vs final optimized routes and record actual changes."""
    init_map: dict[str, RouteStop] = {}
    for route in initial_routes.values():
        for stop in route:
            init_map[stop.job.job_id] = stop

    final_map: dict[str, RouteStop] = {}
    for route in final_routes.values():
        for stop in route:
            final_map[stop.job.job_id] = stop

    changes: dict[str, OptimizationChangeRecord] = {}
    for jid in sorted(final_map.keys()):
        f_stop = final_map[jid]
        i_stop = init_map.get(jid)
        if i_stop is None:
            changes[jid] = OptimizationChangeRecord(
                job_id=jid,
                change_type="newly_assigned",
                previous_technician_id=None,
                new_technician_id=f_stop.technician_id,
                previous_start_min=None,
                new_start_min=f_stop.planned_start_min,
                note=(
                    f"Inserted previously unassigned job {jid} onto {f_stop.technician_id} "
                    f"at {minutes_to_hhmm(f_stop.planned_start_min)}."
                ),
            )
        elif i_stop.technician_id != f_stop.technician_id:
            changes[jid] = OptimizationChangeRecord(
                job_id=jid,
                change_type="reassigned_technician",
                previous_technician_id=i_stop.technician_id,
                new_technician_id=f_stop.technician_id,
                previous_start_min=i_stop.planned_start_min,
                new_start_min=f_stop.planned_start_min,
                note=(
                    f"Reassigned {jid} from {i_stop.technician_id} ({minutes_to_hhmm(i_stop.planned_start_min)}) "
                    f"to {f_stop.technician_id} ({minutes_to_hhmm(f_stop.planned_start_min)})."
                ),
            )
        elif i_stop.planned_start_min != f_stop.planned_start_min or i_stop.from_location_id != f_stop.from_location_id:
            changes[jid] = OptimizationChangeRecord(
                job_id=jid,
                change_type="rescheduled_time_or_order",
                previous_technician_id=i_stop.technician_id,
                new_technician_id=f_stop.technician_id,
                previous_start_min=i_stop.planned_start_min,
                new_start_min=f_stop.planned_start_min,
                note=(
                    f"Updated {jid} on {f_stop.technician_id} from "
                    f"{minutes_to_hhmm(i_stop.planned_start_min)} (after {i_stop.from_location_id}) to "
                    f"{minutes_to_hhmm(f_stop.planned_start_min)} (after {f_stop.from_location_id})."
                ),
            )

    return changes

