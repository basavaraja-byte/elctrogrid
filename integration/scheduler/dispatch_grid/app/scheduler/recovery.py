"""Disruption Recovery & Reproducible Scenario Simulation Engine (D01-D07).

Builds directly on DispatchGrid Modules B and C (`generate_schedule`, `validate_full_schedule`,
`evaluate_schedule_objective`, `generate_candidates_for_job`) without altering their established
algorithms, constraints, or objective hierarchy.

Capabilities:
- Formal specifications for all 7 dataset disruption scenarios (`D01`-`D07`) derived from CSV data.
- Deterministic commitment progression to `event_time_min` preserving `completed`, `in_progress`,
  and `locked=True` future commitments.
- Thread-safe `IdempotentRequestRegistry` preventing duplicate job creation (`D06`) and replaying
  identical idempotent requests safely while rejecting conflicting payload reuse.
- Independent post-recovery verification of `validate_full_schedule` and `evaluate_schedule_objective`.
- Grounded `JobRecoveryExplanation` diagnostics for every affected and target job, including
  rejected candidate reasons where applicable.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from typing import Any

from app.scheduler.candidates import generate_candidates_for_job
from app.scheduler.constraints import (
    RouteStop,
    validate_full_schedule,
    validate_job_data,
)
from app.scheduler.dataset_loader import LoadedDatasetBundle, load_dataset_bundle
from app.scheduler.engine import generate_schedule
from app.scheduler.objective import evaluate_schedule_objective
from app.scheduler.travel import TravelMatrix
from app.schemas.dispatch_recovery import (
    IdempotentJobSubmissionResponse,
    JobRecoveryExplanation,
    RecoveryActionType,
    RejectedCandidateSummary,
    ScenarioRecoveryResult,
    ScenarioSpecification,
    SimulateAllScenariosResponse,
)
from app.schemas.scheduling import (
    DisruptionScenario,
    ExistingAssignment,
    Job,
    JobStatus,
    ReasonCode,
    ScheduledAssignment,
    ScheduleRunResult,
    SchedulerConfig,
    minutes_to_hhmm,
)


COMMON_ENFORCED_CONSTRAINTS: list[str] = [
    "Trade, required skills, and mandatory certifications",
    "Technician service-zone eligibility and active roster status",
    "Technician shift start/end boundaries (no unauthorized overtime)",
    "Technician unavailability intervals (including scenario-injected absences)",
    "Appointment earliest-start and latest-start windows",
    "Positive pairwise/coordinate travel times and non-overlapping route stops",
    "Hard SLA completion deadlines separated from predicted soft-SLA risk",
    "Preservation of completed, active in-progress, and valid locked future commitments",
]


class RecoveryError(Exception):
    """Base exception for disruption recovery and simulation errors."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class IdempotencyConflictError(RecoveryError):
    """Raised when an idempotency_key is reused with a different request payload."""

    def __init__(self, message: str) -> None:
        super().__init__("IDEMPOTENCY_KEY_CONFLICT", message)


class IdempotentRequestRegistry:
    """Thread-safe idempotency store preventing duplicate job creation and duplicate triggers."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._entries: dict[str, tuple[str, Any]] = {}

    @staticmethod
    def fingerprint(payload_dict: dict[str, Any]) -> str:
        canonical = json.dumps(payload_dict, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def check_or_record(
        self,
        idempotency_key: str,
        payload_dict: dict[str, Any],
        compute_fn,
    ) -> tuple[bool, Any]:
        """Return `(is_replay, result)`. Raises `IdempotencyConflictError` on payload mismatch."""
        fp = self.fingerprint(payload_dict)
        with self._lock:
            existing = self._entries.get(idempotency_key)
            if existing is not None:
                stored_fp, stored_res = existing
                if stored_fp != fp:
                    raise IdempotencyConflictError(
                        f"Idempotency key '{idempotency_key}' was already used with a different payload."
                    )
                return True, stored_res

            result = compute_fn()
            self._entries[idempotency_key] = (fp, result)
            return False, result


def _parse_duration_delta(payload: str) -> int:
    match = re.search(r"by\s+(\d+)\s+minute", payload, flags=re.IGNORECASE)
    return int(match.group(1)) if match else 0


def build_scenario_specification(
    sc: DisruptionScenario,
    bundle: LoadedDatasetBundle,
) -> ScenarioSpecification:
    """Construct a formal ScenarioSpecification from dataset metadata without ID hardcoding."""
    hhmm = minutes_to_hhmm(sc.event_time_min)
    scen_unavail = [
        u for u in bundle.all_unavailability if u.scenario_id == sc.scenario_id
    ]
    unavail_desc = [
        f"{u.technician_id} unavailable {minutes_to_hhmm(u.start_min)}-{minutes_to_hhmm(u.end_min)} ({u.reason})"
        for u in scen_unavail
    ]

    if sc.event_type == "technician_unavailable":
        affected = [f"Technician {sc.target_id}"] + unavail_desc + [
            f"Any unlocked future assignments on {sc.target_id} overlapping >= {hhmm}"
        ]
        action = (
            f"Preserve all completed (<= {hhmm}) and active in-progress commitments; apply unavailability "
            f"for {sc.target_id}; evict conflicting future unlocked jobs from {sc.target_id} and "
            "reassign them to eligible technicians via Module B + Module C."
        )
        outcome = (
            f"Completed and in-progress stops remain fixed; {sc.target_id} has zero unlocked work "
            f"overlapping its unavailability window; displaced jobs are reassigned where feasible "
            "with zero hard-constraint violations."
        )
    elif sc.event_type == "urgent_job_arrival":
        s_jobs = bundle.scenario_jobs_by_id.get(sc.scenario_id, [])
        j_desc = (
            f"Urgent {s_jobs[0].priority} job {s_jobs[0].job_id} ({s_jobs[0].duration_min}m, "
            f"skills={s_jobs[0].required_skills}, zone={s_jobs[0].zone}, "
            f"window={minutes_to_hhmm(s_jobs[0].window_start_min or 0)}-{minutes_to_hhmm(s_jobs[0].window_end_min or 1440)}, "
            f"SLA={minutes_to_hhmm(s_jobs[0].sla_deadline_min or 1440)})"
            if s_jobs
            else f"Urgent job {sc.target_id}"
        )
        affected = [j_desc] + unavail_desc
        action = (
            f"Anchor completed/in-progress work at {hhmm}; apply scenario unavailability "
            f"({', '.join(unavail_desc) if unavail_desc else 'none'}); dynamically insert {sc.target_id} "
            "using coordinate-detour travel fallback where matrix pairs are absent, preempting/relocating "
            "lower-priority unlocked work if required."
        )
        outcome = (
            f"{sc.target_id} is scheduled within its window and hard SLA deadline on an eligible "
            "technician; completed/in-progress jobs remain untouched; schedule passes full validation."
        )
    elif sc.event_type == "duration_change":
        delta = _parse_duration_delta(sc.payload)
        affected = [
            f"Job {sc.target_id} (+{delta} min service duration)",
            f"Assigned technician and downstream stops following {sc.target_id} after {hhmm}",
        ]
        action = (
            f"Increase {sc.target_id} duration by +{delta} min at {hhmm}; if {sc.target_id} is "
            "actively in progress, keep its technician and start time protected, extend its completion "
            f"by +{delta} min, and recompute/relocate downstream route stops; if {sc.target_id} is "
            "infeasible under strict hard completion SLA, keep it unassigned with grounded diagnostics."
        )
        outcome = (
            f"Active {sc.target_id} remains on its technician and start time with updated completion "
            "(or remains cleanly unassigned under strict hard SLA when baseline window+duration exceeds SLA); "
            "all downstream stops satisfy shift, window, travel, and SLA rules."
        )
    elif sc.event_type == "job_cancelled":
        affected = [
            f"Cancelled job {sc.target_id}",
            f"Technician previously assigned to {sc.target_id} and pending unassigned jobs in compatible zones",
        ]
        action = (
            f"Mark {sc.target_id} as cancelled at {hhmm} so it consumes zero route capacity; "
            "preserve completed/in-progress work; re-optimize freed route capacity to backfill "
            "eligible unassigned jobs and reduce route travel."
        )
        outcome = (
            f"{sc.target_id} is absent from both assigned and unassigned active lists; freed technician "
            "capacity is cleanly reclaimed without violating protected commitments."
        )
    elif sc.event_type == "job_completed":
        affected = [f"Completed job {sc.target_id} at {hhmm}"]
        action = (
            f"Mark {sc.target_id} as completed at {hhmm} with locked historical timing; run recovery "
            "and bounded local search while strictly prohibiting movement or reassignment of completed work."
        )
        outcome = (
            f"{sc.target_id} remains permanently anchored on its original technician and start time "
            "with status='completed'; full schedule validation passes with zero protected violations."
        )
    elif sc.event_type == "duplicate_request":
        affected = [f"Duplicate job submission target {sc.target_id} (submitted twice with same idempotency key)"]
        action = (
            f"Submit job creation request for {sc.target_id} twice at {hhmm} with identical idempotency key; "
            "accept first request and suppress second duplicate request via IdempotentRequestRegistry "
            "(and engine duplicate-ID guard) so at most one job instance exists."
        )
        outcome = (
            f"Duplicate submission is suppressed; {sc.target_id} exists once (never double-created or "
            "double-assigned); schedule remains valid and objective-consistent."
        )
    elif sc.event_type == "unassignable_job":
        affected = [f"Infeasible job {sc.target_id} evaluated at {hhmm}"]
        action = (
            f"Evaluate {sc.target_id} through Module B static and dynamic constraint checks at {hhmm} "
            "without ID hardcoding; preserve all valid/protected commitments and leave infeasible job unassigned."
        )
        outcome = (
            f"{sc.target_id} remains unassigned with grounded static eligibility diagnostics "
            "(missing skill/authorization and unserved zone); valid schedule commitments remain intact."
        )
    else:
        affected = [sc.target_id]
        action = f"Process disruption '{sc.event_type}' on {sc.target_id} at {hhmm}."
        outcome = "Recovered schedule passes full hard-constraint validation."

    return ScenarioSpecification(
        scenario_id=sc.scenario_id,
        scenario_name=sc.scenario_name,
        event_type=sc.event_type,
        target_id=sc.target_id,
        event_time_min=sc.event_time_min,
        event_time_hhmm=hhmm,
        payload=sc.payload,
        trigger_description=f"[{sc.scenario_id}] {sc.event_type} targeting {sc.target_id} at {hhmm} ({sc.payload})",
        expected_affected_entities=affected,
        expected_recovery_action=action,
        enforced_constraints=list(COMMON_ENFORCED_CONSTRAINTS),
        expected_outcome=outcome,
    )


def get_scenario_specifications(
    bundle: LoadedDatasetBundle | None = None,
) -> dict[str, ScenarioSpecification]:
    """Return formal ScenarioSpecifications for all scenarios in `disruption_scenarios.csv`."""
    ds = bundle if bundle is not None else load_dataset_bundle()
    return {
        sc.scenario_id: build_scenario_specification(sc, ds)
        for sc in sorted(ds.scenarios, key=lambda s: s.scenario_id)
    }


def advance_commitments_to_event_time(
    baseline_assignments: list[ScheduledAssignment],
    event_time_min: int,
    scenario: DisruptionScenario,
    config: SchedulerConfig,
    locked_future_job_ids: set[str] | None = None,
) -> list[ExistingAssignment]:
    """Classify prior schedule assignments into completed, in-progress, locked-future, cancelled, or mutable."""
    locked_future = locked_future_job_ids or set()
    delta_min = _parse_duration_delta(scenario.payload) if scenario.event_type == "duration_change" else 0
    progressed: list[ExistingAssignment] = []

    for a in baseline_assignments:
        jid = a.job_id
        st_lower = a.status.strip().lower()

        if scenario.event_type == "job_cancelled" and jid == scenario.target_id:
            progressed.append(
                ExistingAssignment(
                    job_id=jid,
                    technician_id=a.technician_id,
                    departure_min=a.departure_min,
                    arrival_min=a.arrival_min,
                    planned_start_min=a.planned_start_min,
                    completion_min=a.completion_min,
                    status=JobStatus.CANCELLED.value,
                    locked=False,
                )
            )
            continue

        if scenario.event_type == "job_completed" and jid == scenario.target_id:
            recorded_comp = (
                event_time_min
                if a.planned_start_min <= event_time_min <= a.completion_min
                else a.completion_min
            )
            progressed.append(
                ExistingAssignment(
                    job_id=jid,
                    technician_id=a.technician_id,
                    departure_min=a.departure_min,
                    arrival_min=a.arrival_min,
                    planned_start_min=a.planned_start_min,
                    completion_min=recorded_comp,
                    status=JobStatus.COMPLETED.value,
                    locked=True,
                )
            )
            continue

        if scenario.event_type == "duration_change" and jid == scenario.target_id:
            # If the job already started by event_time_min and its extended duration crosses event_time_min,
            # the technician is actively on site experiencing the duration overrun -> protect in_progress!
            if a.planned_start_min <= event_time_min < (a.completion_min + delta_min):
                progressed.append(
                    ExistingAssignment(
                        job_id=jid,
                        technician_id=a.technician_id,
                        departure_min=a.departure_min,
                        arrival_min=a.arrival_min,
                        planned_start_min=a.planned_start_min,
                        completion_min=a.completion_min + delta_min,
                        status=JobStatus.IN_PROGRESS.value,
                        locked=True,
                    )
                )
                continue

        if st_lower == JobStatus.COMPLETED.value or a.completion_min <= event_time_min:
            progressed.append(
                ExistingAssignment(
                    job_id=jid,
                    technician_id=a.technician_id,
                    departure_min=a.departure_min,
                    arrival_min=a.arrival_min,
                    planned_start_min=a.planned_start_min,
                    completion_min=a.completion_min,
                    status=JobStatus.COMPLETED.value,
                    locked=True,
                )
            )
        elif st_lower == JobStatus.IN_PROGRESS.value or (
            config.protect_in_progress and a.planned_start_min < event_time_min < a.completion_min
        ):
            progressed.append(
                ExistingAssignment(
                    job_id=jid,
                    technician_id=a.technician_id,
                    departure_min=a.departure_min,
                    arrival_min=a.arrival_min,
                    planned_start_min=a.planned_start_min,
                    completion_min=a.completion_min,
                    status=JobStatus.IN_PROGRESS.value,
                    locked=True,
                )
            )
        elif a.is_protected or jid in locked_future:
            progressed.append(
                ExistingAssignment(
                    job_id=jid,
                    technician_id=a.technician_id,
                    departure_min=a.departure_min,
                    arrival_min=a.arrival_min,
                    planned_start_min=a.planned_start_min,
                    completion_min=a.completion_min,
                    status=JobStatus.ASSIGNED.value,
                    locked=True,
                )
            )
        else:
            progressed.append(
                ExistingAssignment(
                    job_id=jid,
                    technician_id=a.technician_id,
                    departure_min=a.departure_min,
                    arrival_min=a.arrival_min,
                    planned_start_min=a.planned_start_min,
                    completion_min=a.completion_min,
                    status=JobStatus.ASSIGNED.value,
                    locked=False,
                )
            )

    return progressed


def _verify_validation_and_objective_consistency(
    res: ScheduleRunResult,
    jobs: list[Job],
    bundle: LoadedDatasetBundle,
    existing_assignments: list[ExistingAssignment],
) -> tuple[bool, list[str], bool]:
    """Independently re-run `validate_full_schedule` and `evaluate_schedule_objective` on recovered routes."""
    cfg = res.config
    elecs_by_id = {e.technician_id: e for e in bundle.electricians}
    cancelled_ids = {
        ex.job_id for ex in existing_assignments if ex.status.strip().lower() == JobStatus.CANCELLED.value
    }

    valid_jobs = {}
    invalid_count = 0
    seen_ids: set[str] = set()
    for j in jobs:
        if j.status.strip().lower() == JobStatus.CANCELLED.value or j.job_id in cancelled_ids:
            cancelled_ids.add(j.job_id)
            continue
        if j.job_id in seen_ids:
            continue
        seen_ids.add(j.job_id)
        rj, errs = validate_job_data(j, cfg)
        if rj is None or errs:
            invalid_count += 1
        else:
            valid_jobs[j.job_id] = rj

    routes: dict[str, list[RouteStop]] = {e.technician_id: [] for e in bundle.electricians}
    existing_prot_map = {ex.job_id: ex for ex in existing_assignments if ex.is_protected}
    for a in res.final_schedule.assignments:
        if a.job_id not in valid_jobs:
            continue
        ex_p = existing_prot_map.get(a.job_id)
        st_l = a.status.strip().lower()
        is_hist = st_l == JobStatus.COMPLETED.value or (
            cfg.protect_in_progress and st_l == JobStatus.IN_PROGRESS.value
        )
        routes[a.technician_id].append(
            RouteStop(
                job=valid_jobs[a.job_id],
                technician_id=a.technician_id,
                from_location_id=a.from_location_id,
                departure_min=a.departure_min,
                arrival_min=a.arrival_min,
                planned_start_min=a.planned_start_min,
                completion_min=a.completion_min,
                travel_time_min=a.travel_time_min,
                travel_source=a.travel_estimate_source,
                status=a.status,
                is_protected=a.is_protected,
                locked_departure_min=a.departure_min if is_hist else (ex_p.departure_min if ex_p else None),
                locked_arrival_min=a.arrival_min if is_hist else (ex_p.arrival_min if ex_p else None),
                locked_completion_min=a.completion_min if st_l == JobStatus.COMPLETED.value else None,
                locked_origin_id=a.from_location_id if a.is_protected else None,
            )
        )

    unavail_by_tech: dict[str, list] = {}
    for u in bundle.unavailability:
        unavail_by_tech.setdefault(u.technician_id, []).append(u)

    t_mat = TravelMatrix(
        entries=bundle.travel_entries,
        electricians=bundle.electricians,
        jobs=jobs,
        allow_coordinate_fallback=cfg.allow_coordinate_travel_fallback,
    )

    full_val = validate_full_schedule(
        routes_by_tech=routes,
        electricians_by_id=elecs_by_id,
        valid_jobs_by_id=valid_jobs,
        unavailability_by_tech=unavail_by_tech,
        existing_assignments=existing_assignments,
        travel_matrix=t_mat,
        config=cfg,
    )

    baseline_map = {
        ex.job_id: (ex.technician_id, ex.planned_start_min)
        for ex in existing_assignments
        if not ex.is_protected
        and ex.status.strip().lower() != JobStatus.CANCELLED.value
        and ex.job_id in valid_jobs
    } or None

    recomputed_obj = evaluate_schedule_objective(
        routes_by_tech=routes,
        electricians=bundle.electricians,
        active_jobs_by_id=valid_jobs,
        validation=full_val,
        config=cfg,
        baseline_assignments=baseline_map,
    )
    if invalid_count:
        recomputed_obj.unassigned_count += invalid_count

    obj_ok = recomputed_obj == res.final_schedule.objective
    return full_val.is_valid, full_val.errors, obj_ok


def _rejected_candidates_for_unassigned_or_eval(
    job: Job,
    routes_Snap: dict[str, list[RouteStop]],
    bundle: LoadedDatasetBundle,
    config: SchedulerConfig,
    limit: int = 8,
) -> list[RejectedCandidateSummary]:
    rj, errs = validate_job_data(job, config)
    if rj is None:
        return [
            RejectedCandidateSummary(technician_id="input_validation", reason_code=e.code, detail=e.detail)
            for e in errs[:limit]
        ]
    unavail_by_tech: dict[str, list] = {}
    for u in bundle.unavailability:
        unavail_by_tech.setdefault(u.technician_id, []).append(u)
    t_mat = TravelMatrix(
        entries=bundle.travel_entries,
        electricians=bundle.electricians,
        jobs=bundle.jobs,
        allow_coordinate_fallback=config.allow_coordinate_travel_fallback,
    )
    ev = generate_candidates_for_job(
        job=rj,
        electricians=bundle.electricians,
        routes_by_tech=routes_Snap,
        unavailability_by_tech=unavail_by_tech,
        travel_matrix=t_mat,
        config=config,
    )
    summaries: list[RejectedCandidateSummary] = []
    seen: set[tuple[str, str]] = set()
    for f in ev.rejection_details:
        tech_hint = "fleet"
        for tok in f.detail.replace("'", " ").replace(":", " ").split():
            if tok.startswith("E") and len(tok) >= 2 and tok[1:].isdigit():
                tech_hint = tok
                break
        key = (tech_hint, f.code.value)
        if key not in seen:
            seen.add(key)
            summaries.append(
                RejectedCandidateSummary(technician_id=tech_hint, reason_code=f.code, detail=f.detail)
            )
        if len(summaries) >= limit:
            break
    return summaries


def simulate_scenario(
    scenario_id: str,
    baseline_result: ScheduleRunResult | None = None,
    config: SchedulerConfig | None = None,
    locked_future_job_ids: list[str] | None = None,
    existing_assignments_override: list[ExistingAssignment] | None = None,
    idempotency_key: str | None = None,
    idempotency_registry: IdempotentRequestRegistry | None = None,
    data_dir: str | None = None,
) -> ScenarioRecoveryResult:
    """Execute a reproducible disruption scenario (`D01`-`D07`) and verify recovery invariants."""
    cfg = config or (baseline_result.config if baseline_result is not None else SchedulerConfig())
    registry = idempotency_registry or IdempotentRequestRegistry()

    if idempotency_key is not None:
        req_fp_payload = {
            "scenario_id": scenario_id,
            "baseline_run_id": baseline_result.run_id if baseline_result else None,
            "locked_future_job_ids": sorted(locked_future_job_ids or []),
            "config": cfg.model_dump(mode="json"),
        }
        is_replay, cached_result = registry.check_or_record(
            idempotency_key=idempotency_key,
            payload_dict=req_fp_payload,
            compute_fn=lambda: _execute_scenario_internal(
                scenario_id=scenario_id,
                baseline_result=baseline_result,
                cfg=cfg,
                locked_future_job_ids=locked_future_job_ids,
                existing_assignments_override=existing_assignments_override,
                outer_idempotency_key=idempotency_key,
                registry=registry,
                data_dir=data_dir,
            ),
        )
        if is_replay:
            return cached_result.model_copy(update={"idempotent_replay": True})
        return cached_result

    return _execute_scenario_internal(
        scenario_id=scenario_id,
        baseline_result=baseline_result,
        cfg=cfg,
        locked_future_job_ids=locked_future_job_ids,
        existing_assignments_override=existing_assignments_override,
        outer_idempotency_key=None,
        registry=registry,
        data_dir=data_dir,
    )


def _execute_scenario_internal(
    scenario_id: str,
    baseline_result: ScheduleRunResult | None,
    cfg: SchedulerConfig,
    locked_future_job_ids: list[str] | None,
    existing_assignments_override: list[ExistingAssignment] | None,
    outer_idempotency_key: str | None,
    registry: IdempotentRequestRegistry,
    data_dir: str | None,
) -> ScenarioRecoveryResult:
    base_bundle = load_dataset_bundle(data_dir=data_dir)
    scenarios_by_id = {s.scenario_id: s for s in base_bundle.scenarios}
    if scenario_id not in scenarios_by_id:
        raise RecoveryError(
            "UNKNOWN_SCENARIO",
            f"Unknown scenario_id '{scenario_id}'. Expected one of {sorted(scenarios_by_id.keys())}.",
        )

    sc = scenarios_by_id[scenario_id]
    spec = build_scenario_specification(sc, base_bundle)

    # 1. Obtain or generate deterministic baseline schedule
    if baseline_result is None:
        base_res = generate_schedule(
            jobs=base_bundle.jobs,
            electricians=base_bundle.electricians,
            travel_times=base_bundle.travel_entries,
            unavailability=base_bundle.unavailability,
            config=cfg,
            run_id=f"baseline-for-{scenario_id.lower()}",
        )
    else:
        base_res = baseline_result

    # 2. Load scenario-mutated bundle (applies D01/D02 unavailability, D02 J101 arrival, D03 duration, D04 cancel)
    scen_bundle = load_dataset_bundle(data_dir=data_dir, scenario_ids=[scenario_id])
    jobs_for_recovery: list[Job] = list(scen_bundle.jobs)

    # 3. Handle D06 duplicate job creation request explicitly through IdempotentRequestRegistry
    duplicate_suppressed = False
    if sc.event_type == "duplicate_request":
        target_job = next((j for j in jobs_for_recovery if j.job_id == sc.target_id), None)
        if target_job is not None:
            sim_idem_key = f"sim-idem-{sc.scenario_id}-{sc.target_id}"
            job_payload = target_job.model_dump(mode="json")
            submitted_jobs: list[Job] = []

            # Submission #1
            replay_1, _ = registry.check_or_record(
                idempotency_key=sim_idem_key,
                payload_dict=job_payload,
                compute_fn=lambda: submitted_jobs.append(target_job) or target_job.job_id,
            )
            # Submission #2 with identical idempotency_key -> must be suppressed!
            replay_2, _ = registry.check_or_record(
                idempotency_key=sim_idem_key,
                payload_dict=job_payload,
                compute_fn=lambda: submitted_jobs.append(target_job.model_copy()) or target_job.job_id,
            )
            duplicate_suppressed = (not replay_1) and replay_2 and (len(submitted_jobs) == 1)

    # 4. Advance baseline commitments to sc.event_time_min (unless caller explicitly supplied existing_assignments)
    if existing_assignments_override is not None:
        progressed_commitments = list(existing_assignments_override)
    else:
        progressed_commitments = advance_commitments_to_event_time(
            baseline_assignments=base_res.final_schedule.assignments,
            event_time_min=sc.event_time_min,
            scenario=sc,
            config=cfg,
            locked_future_job_ids=set(locked_future_job_ids or []),
        )

    # 5. Execute recovery via existing Module B + Module C engine
    rec_res = generate_schedule(
        jobs=jobs_for_recovery,
        electricians=scen_bundle.electricians,
        travel_times=scen_bundle.travel_entries,
        existing_assignments=progressed_commitments,
        unavailability=scen_bundle.unavailability,
        config=cfg,
        run_id=f"recovery-{scenario_id.lower()}-{base_res.run_id}",
        active_scenario_ids=[scenario_id],
        dataset_bundle=scen_bundle,
    )

    # 6. Independently verify full-schedule validation and objective consistency
    val_passed, val_errors, obj_consistent = _verify_validation_and_objective_consistency(
        res=rec_res,
        jobs=jobs_for_recovery,
        bundle=scen_bundle,
        existing_assignments=progressed_commitments,
    )

    # 7. Compute diff & grounded JobRecoveryExplanations
    base_asgn_map: dict[str, ScheduledAssignment] = {
        a.job_id: a for a in base_res.final_schedule.assignments
    }
    rec_asgn_map: dict[str, ScheduledAssignment] = {
        a.job_id: a for a in rec_res.final_schedule.assignments
    }
    prog_by_job: dict[str, ExistingAssignment] = {
        ex.job_id: ex for ex in progressed_commitments
    }
    jobs_by_id: dict[str, Job] = {j.job_id: j for j in jobs_for_recovery}

    # Build RouteStop map for rejected-candidate inspection on key affected/unassigned jobs
    rec_routes_stop: dict[str, list[RouteStop]] = {
        e.technician_id: [] for e in scen_bundle.electricians
    }
    for a in rec_res.final_schedule.assignments:
        rj, _ = validate_job_data(jobs_by_id[a.job_id], cfg)
        if rj is not None:
            rec_routes_stop[a.technician_id].append(
                RouteStop(
                    job=rj,
                    technician_id=a.technician_id,
                    from_location_id=a.from_location_id,
                    departure_min=a.departure_min,
                    arrival_min=a.arrival_min,
                    planned_start_min=a.planned_start_min,
                    completion_min=a.completion_min,
                    travel_time_min=a.travel_time_min,
                    status=a.status,
                    is_protected=a.is_protected,
                )
            )

    preserved_completed: list[str] = []
    preserved_in_progress: list[str] = []
    preserved_locked_future: list[str] = []
    reassigned: list[str] = []
    rescheduled: list[str] = []
    newly_assigned: list[str] = []
    cancelled: list[str] = []
    newly_unassigned: list[str] = []
    affected_jobs_set: set[str] = set()
    affected_techs_set: set[str] = set()
    explanations: dict[str, JobRecoveryExplanation] = {}

    if sc.target_id in {e.technician_id for e in scen_bundle.electricians}:
        affected_techs_set.add(sc.target_id)
    for u in scen_bundle.unavailability:
        if u.scenario_id == scenario_id:
            affected_techs_set.add(u.technician_id)

    all_known_job_ids = sorted(
        set(base_asgn_map.keys()) | set(rec_asgn_map.keys()) | set(jobs_by_id.keys())
    )

    for jid in all_known_job_ids:
        b_a = base_asgn_map.get(jid)
        r_a = rec_asgn_map.get(jid)
        p_ex = prog_by_job.get(jid)
        j_obj = jobs_by_id.get(jid)
        is_target = jid == sc.target_id

        # Cancelled job (e.g. D04 J027)
        if (j_obj and j_obj.status.strip().lower() == JobStatus.CANCELLED.value) or (
            p_ex and p_ex.status.strip().lower() == JobStatus.CANCELLED.value
        ):
            cancelled.append(jid)
            affected_jobs_set.add(jid)
            if b_a is not None:
                affected_techs_set.add(b_a.technician_id)
            explanations[jid] = JobRecoveryExplanation(
                job_id=jid,
                action_type=RecoveryActionType.CANCELLED_REMOVED,
                previous_technician_id=b_a.technician_id if b_a else None,
                previous_start_min=b_a.planned_start_min if b_a else None,
                previous_completion_min=b_a.completion_min if b_a else None,
                explanation=(
                    f"Job {jid} was cancelled at {minutes_to_hhmm(sc.event_time_min)} ({scenario_id}) "
                    + (
                        f"and removed from {b_a.technician_id}'s route ({minutes_to_hhmm(b_a.planned_start_min)}-"
                        f"{minutes_to_hhmm(b_a.completion_min)}), freeing {j_obj.duration_min if j_obj else 0} min of capacity."
                        if b_a
                        else "and excluded from scheduling demand."
                    )
                ),
            )
            continue

        # Currently assigned in recovered schedule
        if r_a is not None:
            r_st = r_a.status.strip().lower()
            if r_st == JobStatus.COMPLETED.value:
                preserved_completed.append(jid)
                if is_target:
                    affected_jobs_set.add(jid)
                    affected_techs_set.add(r_a.technician_id)
                explanations[jid] = JobRecoveryExplanation(
                    job_id=jid,
                    action_type=RecoveryActionType.PRESERVED_COMPLETED,
                    previous_technician_id=b_a.technician_id if b_a else r_a.technician_id,
                    new_technician_id=r_a.technician_id,
                    previous_start_min=b_a.planned_start_min if b_a else r_a.planned_start_min,
                    new_start_min=r_a.planned_start_min,
                    previous_completion_min=b_a.completion_min if b_a else r_a.completion_min,
                    new_completion_min=r_a.completion_min,
                    explanation=(
                        f"Completed job {jid} remained fixed on {r_a.technician_id} starting at "
                        f"{minutes_to_hhmm(r_a.planned_start_min)} (completed {minutes_to_hhmm(r_a.completion_min)})."
                    ),
                )
            elif r_st == JobStatus.IN_PROGRESS.value:
                preserved_in_progress.append(jid)
                if b_a is not None and r_a.completion_min != b_a.completion_min:
                    affected_jobs_set.add(jid)
                    affected_techs_set.add(r_a.technician_id)
                    explanations[jid] = JobRecoveryExplanation(
                        job_id=jid,
                        action_type=RecoveryActionType.DURATION_EXTENDED_IN_PROGRESS,
                        previous_technician_id=b_a.technician_id,
                        new_technician_id=r_a.technician_id,
                        previous_start_min=b_a.planned_start_min,
                        new_start_min=r_a.planned_start_min,
                        previous_completion_min=b_a.completion_min,
                        new_completion_min=r_a.completion_min,
                        explanation=(
                            f"Active in-progress job {jid} stayed protected on {r_a.technician_id} at "
                            f"{minutes_to_hhmm(r_a.planned_start_min)}, while its completion extended from "
                            f"{minutes_to_hhmm(b_a.completion_min)} to {minutes_to_hhmm(r_a.completion_min)} ({scenario_id})."
                        ),
                    )
                else:
                    explanations[jid] = JobRecoveryExplanation(
                        job_id=jid,
                        action_type=RecoveryActionType.PRESERVED_IN_PROGRESS,
                        previous_technician_id=b_a.technician_id if b_a else r_a.technician_id,
                        new_technician_id=r_a.technician_id,
                        previous_start_min=b_a.planned_start_min if b_a else r_a.planned_start_min,
                        new_start_min=r_a.planned_start_min,
                        previous_completion_min=b_a.completion_min if b_a else r_a.completion_min,
                        new_completion_min=r_a.completion_min,
                        explanation=(
                            f"Active in-progress job {jid} remained undisturbed on {r_a.technician_id} "
                            f"({minutes_to_hhmm(r_a.planned_start_min)}-{minutes_to_hhmm(r_a.completion_min)})."
                        ),
                    )
            elif r_a.is_protected:
                preserved_locked_future.append(jid)
                explanations[jid] = JobRecoveryExplanation(
                    job_id=jid,
                    action_type=RecoveryActionType.PRESERVED_LOCKED_FUTURE,
                    previous_technician_id=b_a.technician_id if b_a else r_a.technician_id,
                    new_technician_id=r_a.technician_id,
                    previous_start_min=b_a.planned_start_min if b_a else r_a.planned_start_min,
                    new_start_min=r_a.planned_start_min,
                    previous_completion_min=b_a.completion_min if b_a else r_a.completion_min,
                    new_completion_min=r_a.completion_min,
                    explanation=(
                        f"Locked future commitment {jid} remained pinned on {r_a.technician_id} at "
                        f"{minutes_to_hhmm(r_a.planned_start_min)} and passed all future hard constraints."
                    ),
                )
            elif b_a is None:
                newly_assigned.append(jid)
                affected_jobs_set.add(jid)
                affected_techs_set.add(r_a.technician_id)
                act_type = (
                    RecoveryActionType.NEWLY_INSERTED_URGENT
                    if sc.event_type == "urgent_job_arrival" and is_target
                    else RecoveryActionType.BACKFILLED_FREED_CAPACITY
                )
                rej_cands = (
                    _rejected_candidates_for_unassigned_or_eval(j_obj, rec_routes_stop, scen_bundle, cfg)
                    if j_obj is not None and is_target
                    else []
                )
                explanations[jid] = JobRecoveryExplanation(
                    job_id=jid,
                    action_type=act_type,
                    new_technician_id=r_a.technician_id,
                    new_start_min=r_a.planned_start_min,
                    new_completion_min=r_a.completion_min,
                    explanation=(
                        f"Inserted {r_a.priority.value} job {jid} onto {r_a.technician_id} "
                        f"({minutes_to_hhmm(r_a.planned_start_min)}-{minutes_to_hhmm(r_a.completion_min)}, "
                        f"SLA slack {r_a.slack_min} min)."
                    ),
                    rejected_candidates=rej_cands,
                )
            elif b_a.technician_id != r_a.technician_id:
                reassigned.append(jid)
                affected_jobs_set.add(jid)
                affected_techs_set.add(b_a.technician_id)
                affected_techs_set.add(r_a.technician_id)
                explanations[jid] = JobRecoveryExplanation(
                    job_id=jid,
                    action_type=RecoveryActionType.REASSIGNED_TECHNICIAN,
                    previous_technician_id=b_a.technician_id,
                    new_technician_id=r_a.technician_id,
                    previous_start_min=b_a.planned_start_min,
                    new_start_min=r_a.planned_start_min,
                    previous_completion_min=b_a.completion_min,
                    new_completion_min=r_a.completion_min,
                    explanation=(
                        f"Reassigned {jid} from {b_a.technician_id} ({minutes_to_hhmm(b_a.planned_start_min)}) "
                        f"to eligible technician {r_a.technician_id} ({minutes_to_hhmm(r_a.planned_start_min)}-"
                        f"{minutes_to_hhmm(r_a.completion_min)}) during {scenario_id} recovery."
                    ),
                )
            elif b_a.planned_start_min != r_a.planned_start_min or b_a.completion_min != r_a.completion_min:
                rescheduled.append(jid)
                affected_jobs_set.add(jid)
                affected_techs_set.add(r_a.technician_id)
                explanations[jid] = JobRecoveryExplanation(
                    job_id=jid,
                    action_type=RecoveryActionType.RESCHEDULED_TIME,
                    previous_technician_id=b_a.technician_id,
                    new_technician_id=r_a.technician_id,
                    previous_start_min=b_a.planned_start_min,
                    new_start_min=r_a.planned_start_min,
                    previous_completion_min=b_a.completion_min,
                    new_completion_min=r_a.completion_min,
                    explanation=(
                        f"Adjusted {jid} on {r_a.technician_id} from "
                        f"{minutes_to_hhmm(b_a.planned_start_min)}-{minutes_to_hhmm(b_a.completion_min)} to "
                        f"{minutes_to_hhmm(r_a.planned_start_min)}-{minutes_to_hhmm(r_a.completion_min)}."
                    ),
                )
            elif is_target and sc.event_type == "duplicate_request":
                affected_jobs_set.add(jid)
                affected_techs_set.add(r_a.technician_id)
                explanations[jid] = JobRecoveryExplanation(
                    job_id=jid,
                    action_type=RecoveryActionType.DEDUPLICATED_REQUEST,
                    previous_technician_id=b_a.technician_id,
                    new_technician_id=r_a.technician_id,
                    previous_start_min=b_a.planned_start_min,
                    new_start_min=r_a.planned_start_min,
                    previous_completion_min=b_a.completion_min,
                    new_completion_min=r_a.completion_min,
                    explanation=(
                        f"Duplicate submission for {jid} suppressed via idempotency key; single scheduled "
                        f"instance preserved on {r_a.technician_id} ({minutes_to_hhmm(r_a.planned_start_min)})."
                    ),
                )
            continue

        # Unassigned in recovered schedule
        u_rep = rec_res.unassigned_reasons.get(jid)
        if b_a is not None:
            newly_unassigned.append(jid)
            affected_jobs_set.add(jid)
            affected_techs_set.add(b_a.technician_id)
            rej_cands = (
                _rejected_candidates_for_unassigned_or_eval(j_obj, rec_routes_stop, scen_bundle, cfg)
                if j_obj is not None
                else []
            )
            explanations[jid] = JobRecoveryExplanation(
                job_id=jid,
                action_type=RecoveryActionType.UNASSIGNED_AFTER_DISRUPTION,
                previous_technician_id=b_a.technician_id,
                previous_start_min=b_a.planned_start_min,
                previous_completion_min=b_a.completion_min,
                explanation=(
                    f"Job {jid} (previously on {b_a.technician_id} at {minutes_to_hhmm(b_a.planned_start_min)}) "
                    f"could not be reassigned after {scenario_id}: {u_rep.summary if u_rep else 'no feasible slot'}."
                ),
                rejected_candidates=rej_cands,
            )
        elif is_target:
            affected_jobs_set.add(jid)
            rej_cands = (
                _rejected_candidates_for_unassigned_or_eval(j_obj, rec_routes_stop, scen_bundle, cfg)
                if j_obj is not None
                else []
            )
            if sc.event_type == "duplicate_request":
                explanations[jid] = JobRecoveryExplanation(
                    job_id=jid,
                    action_type=RecoveryActionType.DEDUPLICATED_REQUEST,
                    explanation=(
                        f"Duplicate submission for {jid} suppressed via idempotency key (exactly 1 copy retained); "
                        f"{jid} remained unassigned under current {cfg.sla_mode} SLA policy: "
                        f"{u_rep.summary if u_rep else 'no feasible slot'}."
                    ),
                    rejected_candidates=rej_cands,
                )
            else:
                explanations[jid] = JobRecoveryExplanation(
                    job_id=jid,
                    action_type=RecoveryActionType.LEFT_UNASSIGNED,
                    explanation=(
                        u_rep.summary
                        if u_rep is not None
                        else f"Job {jid} has zero feasible technician/slot candidates."
                    ),
                    rejected_candidates=rej_cands,
                )

    summary = (
        f"[{sc.scenario_id} — {sc.scenario_name} @ {minutes_to_hhmm(sc.event_time_min)}] "
        f"Assigned={len(rec_res.assigned_job_ids)} (baseline={len(base_res.assigned_job_ids)}), "
        f"Unassigned={len(rec_res.unassigned_job_ids)}, "
        f"Preserved(completed={len(preserved_completed)}, in_progress={len(preserved_in_progress)}, "
        f"locked_future={len(preserved_locked_future)}), "
        f"Reassigned={len(reassigned)}, Rescheduled={len(rescheduled)}, "
        f"NewlyAssigned={len(newly_assigned)}, Cancelled={len(cancelled)}, "
        f"DuplicateSuppressed={duplicate_suppressed}, Valid={val_passed}, ObjectiveConsistent={obj_consistent}."
    )

    return ScenarioRecoveryResult(
        scenario_id=sc.scenario_id,
        scenario_name=sc.scenario_name,
        event_type=sc.event_type,
        target_id=sc.target_id,
        event_time_min=sc.event_time_min,
        event_time_hhmm=minutes_to_hhmm(sc.event_time_min),
        idempotency_key=outer_idempotency_key,
        idempotent_replay=False,
        duplicate_request_suppressed=duplicate_suppressed,
        specification=spec,
        affected_job_ids=sorted(affected_jobs_set),
        affected_technician_ids=sorted(affected_techs_set),
        preserved_completed_job_ids=sorted(preserved_completed),
        preserved_in_progress_job_ids=sorted(preserved_in_progress),
        preserved_locked_future_job_ids=sorted(preserved_locked_future),
        reassigned_job_ids=sorted(reassigned),
        rescheduled_job_ids=sorted(rescheduled),
        newly_assigned_job_ids=sorted(newly_assigned),
        cancelled_job_ids=sorted(cancelled),
        newly_unassigned_job_ids=sorted(newly_unassigned),
        recovery_summary=summary,
        job_recovery_explanations=explanations,
        baseline_run_id=base_res.run_id,
        recovered_schedule_run=rec_res,
        validation_passed=val_passed,
        validation_errors=val_errors,
        objective_consistent=obj_consistent,
    )


def simulate_all_scenarios(
    scenario_ids: list[str] | None = None,
    config: SchedulerConfig | None = None,
    data_dir: str | None = None,
) -> SimulateAllScenariosResponse:
    """Reproducibly simulate `D01`-`D07` from a single deterministic baseline schedule."""
    cfg = config or SchedulerConfig()
    base_bundle = load_dataset_bundle(data_dir=data_dir)
    base_res = generate_schedule(
        jobs=base_bundle.jobs,
        electricians=base_bundle.electricians,
        travel_times=base_bundle.travel_entries,
        unavailability=base_bundle.unavailability,
        config=cfg,
        run_id="baseline-simulation-suite",
    )

    target_scenarios = scenario_ids or [s.scenario_id for s in base_bundle.scenarios]
    registry = IdempotentRequestRegistry()
    results: dict[str, ScenarioRecoveryResult] = {}

    for sid in target_scenarios:
        results[sid] = simulate_scenario(
            scenario_id=sid,
            baseline_result=base_res,
            config=cfg,
            idempotency_registry=registry,
            data_dir=data_dir,
        )

    all_valid = all(r.validation_passed and r.recovered_schedule_run.is_valid_for_commitment for r in results.values())
    all_obj_ok = all(r.objective_consistent for r in results.values())

    return SimulateAllScenariosResponse(
        baseline_run_id=base_res.run_id,
        baseline_assigned_count=len(base_res.assigned_job_ids),
        baseline_unassigned_count=len(base_res.unassigned_job_ids),
        all_validations_passed=all_valid,
        all_objectives_consistent=all_obj_ok,
        results_by_scenario=results,
    )


def submit_idempotent_job(
    idempotency_key: str,
    job: Job,
    registry: IdempotentRequestRegistry,
    baseline_result: ScheduleRunResult | None = None,
    event_time_min: int | None = None,
    reschedule_immediately: bool = True,
    config: SchedulerConfig | None = None,
    data_dir: str | None = None,
) -> IdempotentJobSubmissionResponse:
    """Submit a new or duplicate job request idempotently (API & programmatic D06 support)."""
    cfg = config or (baseline_result.config if baseline_result is not None else SchedulerConfig())
    fp_payload = {
        "job": job.model_dump(mode="json"),
        "baseline_run_id": baseline_result.run_id if baseline_result else None,
        "event_time_min": event_time_min,
        "reschedule_immediately": reschedule_immediately,
        "config": cfg.model_dump(mode="json"),
    }

    def _create_once() -> ScheduleRunResult | None:
        if not reschedule_immediately:
            return None
        bundle = load_dataset_bundle(data_dir=data_dir)
        base_res = baseline_result or generate_schedule(
            jobs=bundle.jobs,
            electricians=bundle.electricians,
            travel_times=bundle.travel_entries,
            unavailability=bundle.unavailability,
            config=cfg,
        )
        merged_jobs = list(bundle.jobs)
        if all(existing_j.job_id != job.job_id for existing_j in merged_jobs):
            merged_jobs.append(job)

        eff_time = event_time_min if event_time_min is not None else 0
        dummy_sc = DisruptionScenario(
            scenario_id="IDEM_JOB",
            scenario_name="Idempotent Job Submission",
            event_type="urgent_job_arrival",
            target_id=job.job_id,
            event_time_min=eff_time,
        )
        progressed = advance_commitments_to_event_time(
            baseline_assignments=base_res.final_schedule.assignments,
            event_time_min=eff_time,
            scenario=dummy_sc,
            config=cfg,
        )
        return generate_schedule(
            jobs=merged_jobs,
            electricians=bundle.electricians,
            travel_times=bundle.travel_entries,
            existing_assignments=progressed,
            unavailability=bundle.unavailability,
            config=cfg,
        )

    is_replay, sched_run = registry.check_or_record(
        idempotency_key=idempotency_key,
        payload_dict=fp_payload,
        compute_fn=_create_once,
    )
    if is_replay:
        return IdempotentJobSubmissionResponse(
            idempotency_key=idempotency_key,
            job_id=job.job_id,
            created=False,
            duplicate_suppressed=True,
            schedule_run=sched_run,
            message=f"Duplicate request suppressed for idempotency_key='{idempotency_key}'; returning original result for job '{job.job_id}'.",
        )
    return IdempotentJobSubmissionResponse(
        idempotency_key=idempotency_key,
        job_id=job.job_id,
        created=True,
        duplicate_suppressed=False,
        schedule_run=sched_run,
        message=f"Processed job '{job.job_id}' once under idempotency_key='{idempotency_key}'.",
    )

