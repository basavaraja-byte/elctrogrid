"""Unit and integration tests for Module C bounded local search optimizer (Section 15)."""

from __future__ import annotations

from app.scheduler.candidates import StopSpec, build_timed_route
from app.scheduler.constraints import validate_full_schedule, validate_job_data
from app.scheduler.engine import generate_schedule
from app.scheduler.objective import (
    evaluate_schedule_objective,
    is_strictly_better_objective,
    lexicographic_objective_key,
)
from app.scheduler.optimizer import run_bounded_local_search
from app.scheduler.travel import TravelMatrix
from app.schemas.scheduling import (
    Electrician,
    ExistingAssignment,
    Job,
    ReasonCode,
    SchedulerConfig,
    TerminationReason,
    TravelEntry,
)


def _complete_travel(pairs: dict[tuple[str, str], int], locs: list[str], default: int = 30) -> list[TravelEntry]:
    entries: list[TravelEntry] = []
    for u in locs:
        for v in locs:
            if u == v:
                t = 0
            else:
                t = pairs.get((u, v), pairs.get((v, u), default))
            entries.append(TravelEntry(from_location_id=u, to_location_id=v, travel_time_min=t))
    return entries


def test_optimizer_accepts_valid_swap_and_reduces_travel() -> None:
    """Construct a suboptimal initial schedule and verify Module C swaps jobs to cut travel."""
    cfg = SchedulerConfig()
    e1 = Electrician(
        technician_id="E1",
        skills=["fault_diagnosis"],
        eligible_zones=["Central"],
        shift_start_min=480,
        shift_end_min=960,
    )
    e2 = Electrician(
        technician_id="E2",
        skills=["fault_diagnosis"],
        eligible_zones=["Central"],
        shift_start_min=480,
        shift_end_min=960,
    )
    j1 = Job(
        job_id="J1",
        required_skills=["fault_diagnosis"],
        priority="Normal",
        duration_min=60,
        zone="Central",
        window_start_min=540,
        window_end_min=660,
        sla_deadline_min=840,
    )
    j2 = Job(
        job_id="J2",
        required_skills=["fault_diagnosis"],
        priority="Normal",
        duration_min=60,
        zone="Central",
        window_start_min=540,
        window_end_min=660,
        sla_deadline_min=840,
    )
    # E1 is right next to J2 (5m) and far from J1 (45m); E2 is right next to J1 (5m) and far from J2 (45m)
    tt_entries = _complete_travel(
        {
            ("HOME_E1", "J1"): 45,
            ("HOME_E1", "J2"): 5,
            ("HOME_E2", "J1"): 5,
            ("HOME_E2", "J2"): 45,
            ("J1", "J2"): 50,
        },
        ["HOME_E1", "HOME_E2", "J1", "J2"],
    )
    t_matrix = TravelMatrix(entries=tt_entries)
    rj1, _ = validate_job_data(j1, cfg)
    rj2, _ = validate_job_data(j2, cfg)
    assert rj1 is not None and rj2 is not None

    # Deliberately suboptimal initial routes: E1->J1 (45m), E2->J2 (45m) = 90m total travel
    r_e1, _ = build_timed_route(e1, [StopSpec(job=rj1)], [], t_matrix, cfg)
    r_e2, _ = build_timed_route(e2, [StopSpec(job=rj2)], [], t_matrix, cfg)
    assert r_e1 is not None and r_e2 is not None

    outcome = run_bounded_local_search(
        initial_routes={"E1": r_e1, "E2": r_e2},
        electricians=[e1, e2],
        active_jobs_by_id={"J1": rj1, "J2": rj2},
        unavailability_by_tech={},
        existing_assignments=[],
        travel_matrix=t_matrix,
        config=cfg,
    )
    assert outcome.moves_accepted >= 1
    assert outcome.final_objective.raw_total_travel_min == 10
    assert outcome.routes_by_tech["E1"][0].job.job_id == "J2"
    assert outcome.routes_by_tech["E2"][0].job.job_id == "J1"


def test_optimizer_ejection_relocation_increases_coverage() -> None:
    """Verify local search relocates a flexible blocking job so an unassigned job can be inserted."""
    cfg = SchedulerConfig()
    e_spec = Electrician(
        technician_id="E_SPEC",
        skills=["fault_diagnosis", "ev_charger_installation"],
        eligible_zones=["Central"],
        shift_start_min=540,
        shift_end_min=660,
    )
    e_gen = Electrician(
        technician_id="E_GEN",
        skills=["fault_diagnosis"],
        eligible_zones=["Central"],
        shift_start_min=540,
        shift_end_min=660,
    )
    j_flex = Job(
        job_id="J_FLEX",
        required_skills=["fault_diagnosis"],
        priority="Normal",
        duration_min=90,
        zone="Central",
        window_start_min=555,
        window_end_min=570,
        sla_deadline_min=720,
    )
    j_ev = Job(
        job_id="J_EV",
        required_skills=["ev_charger_installation"],
        priority="Normal",
        duration_min=90,
        zone="Central",
        window_start_min=555,
        window_end_min=570,
        sla_deadline_min=720,
    )
    tt_entries = _complete_travel({}, ["HOME_E_SPEC", "HOME_E_GEN", "J_FLEX", "J_EV"], default=15)
    t_matrix = TravelMatrix(entries=tt_entries)
    rj_flex, _ = validate_job_data(j_flex, cfg)
    rj_ev, _ = validate_job_data(j_ev, cfg)
    assert rj_flex is not None and rj_ev is not None

    # Initial state has J_FLEX blocking E_SPEC while E_GEN is empty and J_EV is unassigned!
    r_spec, _ = build_timed_route(e_spec, [StopSpec(job=rj_flex)], [], t_matrix, cfg)
    assert r_spec is not None

    outcome = run_bounded_local_search(
        initial_routes={"E_SPEC": r_spec, "E_GEN": []},
        electricians=[e_spec, e_gen],
        active_jobs_by_id={"J_FLEX": rj_flex, "J_EV": rj_ev},
        unavailability_by_tech={},
        existing_assignments=[],
        travel_matrix=t_matrix,
        config=cfg,
    )
    assert outcome.final_objective.assigned_count == 2
    assert outcome.final_objective.unassigned_count == 0
    assert outcome.routes_by_tech["E_SPEC"][0].job.job_id == "J_EV"
    assert outcome.routes_by_tech["E_GEN"][0].job.job_id == "J_FLEX"


def test_optimizer_rejects_non_improving_and_invalid_moves() -> None:
    """When schedule is already uniquely optimal, optimizer accepts 0 moves and terminates cleanly."""
    e1 = Electrician(
        technician_id="E1",
        skills=["fault_diagnosis"],
        eligible_zones=["Central"],
        shift_start_min=480,
        shift_end_min=960,
    )
    j1 = Job(
        job_id="J1",
        required_skills=["fault_diagnosis"],
        priority="High",
        duration_min=60,
        zone="Central",
        window_start_min=540,
        window_end_min=600,
        sla_deadline_min=720,
    )
    tt = [TravelEntry(from_location_id="HOME_E1", to_location_id="J1", travel_time_min=15)]
    res = generate_schedule(jobs=[j1], electricians=[e1], travel_times=tt)
    assert res.optimization.moves_accepted == 0
    assert res.optimization.termination_reason == TerminationReason.LOCAL_OPTIMUM_REACHED
    assert not res.optimization.improved


def test_optimizer_respects_objective_hierarchy_coverage_over_travel() -> None:
    """Verify objective comparator never prefers lower travel at the cost of dropping a job."""
    e1 = Electrician(
        technician_id="E1",
        skills=["fault_diagnosis"],
        eligible_zones=["Central"],
        shift_start_min=480,
        shift_end_min=960,
    )
    j_far = Job(
        job_id="J_FAR",
        required_skills=["fault_diagnosis"],
        priority="Low",
        duration_min=60,
        zone="Central",
        window_start_min=540,
        window_end_min=660,
        sla_deadline_min=840,
    )
    tt = [TravelEntry(from_location_id="HOME_E1", to_location_id="J_FAR", travel_time_min=55)]
    res_assigned = generate_schedule(
        jobs=[j_far],
        electricians=[e1],
        travel_times=tt,
        config=SchedulerConfig(w_travel=10.0),  # Even huge travel weight must not drop coverage!
    )
    assert res_assigned.assigned_job_ids == ["J_FAR"]
    assert res_assigned.final_schedule.total_travel_min == 55

    # Compare against an empty-schedule objective directly
    empty_obj = res_assigned.final_schedule.objective.model_copy(
        update={
            "weighted_cost": 0.0,
            "travel_cost_norm": 0.0,
            "raw_total_travel_min": 0,
            "assigned_count": 0,
            "unassigned_count": 1,
            "unassigned_by_priority": {"Critical": 0, "High": 0, "Normal": 0, "Low": 1},
        }
    )
    assert not is_strictly_better_objective(empty_obj, res_assigned.final_schedule.objective)


def test_optimizer_preserves_protected_commitments_and_respects_budgets() -> None:
    """Verify protected commitments never move even when swapping them would cut 80 min travel."""
    cfg = SchedulerConfig(max_iterations=3, max_runtime_seconds=2.0)
    e1 = Electrician(
        technician_id="E1",
        skills=["fault_diagnosis"],
        eligible_zones=["Central"],
        shift_start_min=480,
        shift_end_min=960,
    )
    e2 = Electrician(
        technician_id="E2",
        skills=["fault_diagnosis"],
        eligible_zones=["Central"],
        shift_start_min=480,
        shift_end_min=960,
    )
    j_prot = Job(
        job_id="J_PROT",
        required_skills=["fault_diagnosis"],
        priority="Normal",
        duration_min=60,
        zone="Central",
        window_start_min=540,
        window_end_min=660,
        sla_deadline_min=840,
        status="in_progress",
    )
    j_free = Job(
        job_id="J_FREE",
        required_skills=["fault_diagnosis"],
        priority="Normal",
        duration_min=60,
        zone="Central",
        window_start_min=540,
        window_end_min=660,
        sla_deadline_min=840,
    )
    tt = _complete_travel(
        {
            ("HOME_E1", "J_PROT"): 50,
            ("HOME_E1", "J_FREE"): 5,
            ("HOME_E2", "J_PROT"): 5,
            ("HOME_E2", "J_FREE"): 50,
        },
        ["HOME_E1", "HOME_E2", "J_PROT", "J_FREE"],
    )
    existing = [
        ExistingAssignment(
            job_id="J_PROT",
            technician_id="E1",
            planned_start_min=540,
            status="in_progress",
            locked=True,
        )
    ]
    res = generate_schedule(
        jobs=[j_prot, j_free],
        electricians=[e1, e2],
        travel_times=tt,
        existing_assignments=existing,
        config=cfg,
    )
    assert res.is_valid_for_commitment
    assert res.optimization.iterations_executed <= 3
    by_job = {a.job_id: a for a in res.final_schedule.assignments}
    assert by_job["J_PROT"].technician_id == "E1"
    assert by_job["J_PROT"].planned_start_min == 540


def test_optimizer_determinism_on_repeated_runs() -> None:
    e1 = Electrician(
        technician_id="E1",
        skills=["fault_diagnosis"],
        eligible_zones=["North"],
        shift_start_min=480,
        shift_end_min=960,
    )
    e2 = Electrician(
        technician_id="E2",
        skills=["fault_diagnosis"],
        eligible_zones=["North"],
        shift_start_min=480,
        shift_end_min=960,
    )
    jobs = [
        Job(
            job_id=f"J{i}",
            required_skills=["fault_diagnosis"],
            priority="Normal",
            duration_min=60,
            zone="North",
            window_start_min=540 + (i % 3) * 60,
            window_end_min=780,
            sla_deadline_min=900,
        )
        for i in range(1, 7)
    ]
    locs = ["HOME_E1", "HOME_E2"] + [j.job_id for j in jobs]
    pairs = {("HOME_E1", f"J{i}"): 10 + (i * 7) % 25 for i in range(1, 7)}
    pairs.update({("HOME_E2", f"J{i}"): 30 - (i * 5) % 20 for i in range(1, 7)})
    tt = _complete_travel(pairs, locs, default=15)

    r1 = generate_schedule(jobs=jobs, electricians=[e1, e2], travel_times=tt)
    r2 = generate_schedule(jobs=jobs, electricians=[e1, e2], travel_times=tt)

    sig1 = [(a.job_id, a.technician_id, a.planned_start_min) for a in r1.final_schedule.assignments]
    sig2 = [(a.job_id, a.technician_id, a.planned_start_min) for a in r2.final_schedule.assignments]
    assert sig1 == sig2
    assert r1.final_schedule.objective.weighted_cost == r2.final_schedule.objective.weighted_cost


def test_soft_sla_breach_vs_unassigned_coverage_policy_explicit() -> None:
    """Under soft-SLA mode, assigning a feasible job with a predicted soft-SLA breach beats leaving it unassigned.

    Also verifies:
    - Hard-deadline handling remains strictly separate (rejects late candidate under sla_mode='hard').
    - Predicted soft-SLA breaches are recorded as planning-time risk (hard_sla_violation_count == 0).
    - Priority-sensitive coverage remains deterministic even when higher-priority work has negative soft slack.
    """
    soft_cfg = SchedulerConfig(sla_mode="soft")
    e1 = Electrician(
        technician_id="E1",
        skills=["fault_diagnosis"],
        eligible_zones=["Central"],
        shift_start_min=480,
        shift_end_min=960,
    )
    # Earliest start 600 + 90m duration = 690 > soft sla_deadline_min 660 (slack = -30m)
    j_soft_late = Job(
        job_id="J_SOFT_LATE",
        required_skills=["fault_diagnosis"],
        priority="Normal",
        duration_min=90,
        zone="Central",
        window_start_min=600,
        window_end_min=720,
        sla_deadline_min=660,
    )
    tt_entries = _complete_travel({}, ["HOME_E1", "J_SOFT_LATE"], default=15)
    t_matrix = TravelMatrix(entries=tt_entries)
    rj_soft, errs = validate_job_data(j_soft_late, soft_cfg)
    assert not errs and rj_soft is not None and not rj_soft.is_hard_deadline

    # Schedule A: assigns J_SOFT_LATE with a predicted soft-SLA breach (slack = -30)
    assigned_route, route_err = build_timed_route(e1, [StopSpec(job=rj_soft)], [], t_matrix, soft_cfg)
    assert route_err is None and assigned_route is not None
    routes_assigned = {"E1": assigned_route}
    val_assigned = validate_full_schedule(
        routes_by_tech=routes_assigned,
        electricians_by_id={"E1": e1},
        valid_jobs_by_id={"J_SOFT_LATE": rj_soft},
        unavailability_by_tech={},
        existing_assignments=[],
        travel_matrix=t_matrix,
        config=soft_cfg,
    )
    assert val_assigned.is_valid
    assert val_assigned.hard_violation_count == 0
    assert val_assigned.hard_sla_violation_count == 0

    # Schedule B: otherwise identical valid schedule that leaves J_SOFT_LATE unassigned
    routes_unassigned: dict[str, list] = {"E1": []}
    val_unassigned = validate_full_schedule(
        routes_by_tech=routes_unassigned,
        electricians_by_id={"E1": e1},
        valid_jobs_by_id={"J_SOFT_LATE": rj_soft},
        unavailability_by_tech={},
        existing_assignments=[],
        travel_matrix=t_matrix,
        config=soft_cfg,
    )
    assert val_unassigned.is_valid

    obj_assigned = evaluate_schedule_objective(
        routes_by_tech=routes_assigned,
        electricians=[e1],
        active_jobs_by_id={"J_SOFT_LATE": rj_soft},
        validation=val_assigned,
        config=soft_cfg,
    )
    obj_unassigned = evaluate_schedule_objective(
        routes_by_tech=routes_unassigned,
        electricians=[e1],
        active_jobs_by_id={"J_SOFT_LATE": rj_soft},
        validation=val_unassigned,
        config=soft_cfg,
    )

    assert obj_assigned.assigned_count == 1
    assert obj_assigned.unassigned_count == 0
    assert obj_assigned.predicted_soft_sla_breach_count == 1
    assert obj_assigned.hard_sla_violation_count == 0  # Predicted soft breach != actual/hard violation
    assert obj_unassigned.assigned_count == 0
    assert obj_unassigned.unassigned_count == 1
    assert obj_unassigned.predicted_soft_sla_breach_count == 0

    # Policy check: Schedule A (assigning the job) strictly beats Schedule B (leaving it unassigned)
    assert lexicographic_objective_key(obj_assigned) < lexicographic_objective_key(obj_unassigned)
    assert is_strictly_better_objective(obj_assigned, obj_unassigned)
    assert not is_strictly_better_objective(obj_unassigned, obj_assigned)

    # Optimizer integration check: starting from empty Schedule B, local search inserts J_SOFT_LATE
    ls_outcome = run_bounded_local_search(
        initial_routes=routes_unassigned,
        electricians=[e1],
        active_jobs_by_id={"J_SOFT_LATE": rj_soft},
        unavailability_by_tech={},
        existing_assignments=[],
        travel_matrix=t_matrix,
        config=soft_cfg,
    )
    assert ls_outcome.moves_accepted == 1
    assert ls_outcome.final_objective.assigned_count == 1
    assert ls_outcome.final_objective.predicted_soft_sla_breach_count == 1

    # Priority-sensitive determinism under soft-SLA mode: single slot on E_TIGHT prefers Critical
    # (even with predicted soft-SLA breach) over Low (with positive slack)
    e_tight = Electrician(
        technician_id="E_TIGHT",
        skills=["fault_diagnosis"],
        eligible_zones=["Central"],
        shift_start_min=585,
        shift_end_min=695,
    )
    j_crit_late = Job(
        job_id="J_CRIT_SOFT",
        required_skills=["fault_diagnosis"],
        priority="Critical",
        duration_min=90,
        zone="Central",
        window_start_min=600,
        window_end_min=605,
        sla_deadline_min=660,  # Finishes at 690 -> slack -30
    )
    j_low_easy = Job(
        job_id="J_LOW_EASY",
        required_skills=["fault_diagnosis"],
        priority="Low",
        duration_min=90,
        zone="Central",
        window_start_min=600,
        window_end_min=605,
        sla_deadline_min=900,  # Finishes at 690 -> slack +210
    )
    tt_prio = _complete_travel({}, ["HOME_E_TIGHT", "J_CRIT_SOFT", "J_LOW_EASY"], default=15)
    res_prio = generate_schedule(
        jobs=[j_low_easy, j_crit_late],
        electricians=[e_tight],
        travel_times=tt_prio,
        config=soft_cfg,
    )
    assert res_prio.assigned_job_ids == ["J_CRIT_SOFT"]
    assert res_prio.unassigned_job_ids == ["J_LOW_EASY"]
    assert res_prio.final_schedule.predicted_soft_sla_breach_count == 1
    assert res_prio.final_schedule.hard_sla_violation_count == 0

    # Hard-deadline separation check: under sla_mode='hard', J_SOFT_LATE is rejected before scoring
    res_hard = generate_schedule(
        jobs=[j_soft_late],
        electricians=[e1],
        travel_times=tt_entries,
        config=SchedulerConfig(sla_mode="hard"),
    )
    assert res_hard.assigned_job_ids == []
    assert res_hard.unassigned_reasons["J_SOFT_LATE"].primary_reason_code == ReasonCode.SLA_DEADLINE_INFEASIBLE


def test_every_accepted_optimizer_move_passes_full_schedule_validation(monkeypatch) -> None:
    """Instrument validate_full_schedule inside Module C to prove every accepted move is full-schedule valid,
    and verify that any cost-improving candidate failing validate_full_schedule is rejected.
    """
    import app.scheduler.optimizer as opt_mod
    from app.scheduler.constraints import FullScheduleValidationResult
    from app.scheduler.dataset_loader import load_dataset_bundle
    from app.scheduler.optimizer import compute_schedule_signature

    real_validate = opt_mod.validate_full_schedule
    validated_valid_signatures: set = set()
    validation_calls: list[bool] = []

    def tracking_validate(*args, **kwargs):
        res = real_validate(*args, **kwargs)
        validation_calls.append(res.is_valid)
        if res.is_valid:
            assert res.hard_violation_count == 0
            assert res.protected_violation_count == 0
            assert res.hard_sla_violation_count == 0
            routes = kwargs.get("routes_by_tech") if "routes_by_tech" in kwargs else args[0]
            validated_valid_signatures.add(compute_schedule_signature(routes))
        return res

    monkeypatch.setattr(opt_mod, "validate_full_schedule", tracking_validate)

    # 1. Run full 100-job baseline schedule + local search optimization and verify every accepted state was validated
    bundle = load_dataset_bundle()
    run_res = generate_schedule(
        jobs=bundle.jobs,
        electricians=bundle.electricians,
        travel_times=bundle.travel_entries,
    )
    assert run_res.optimization.moves_accepted >= 1
    assert run_res.is_valid_for_commitment
    # Initial state + every accepted move passed tracking_validate
    assert sum(1 for ok in validation_calls if ok) >= 1 + run_res.optimization.moves_accepted

    final_routes_reconstructed = {e.technician_id: [] for e in bundle.electricians}
    cfg = run_res.config
    valid_jobs = {}
    for j in bundle.jobs:
        rj, _ = validate_job_data(j, cfg)
        if rj is not None:
            valid_jobs[j.job_id] = rj
    for a in run_res.final_schedule.assignments:
        from app.scheduler.constraints import RouteStop

        final_routes_reconstructed[a.technician_id].append(
            RouteStop(
                job=valid_jobs[a.job_id],
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
    assert compute_schedule_signature(final_routes_reconstructed) in validated_valid_signatures

    # 2. Verify gate enforcement: if validate_full_schedule rejects candidate moves, 0 moves are accepted
    e1 = Electrician(
        technician_id="E1",
        skills=["fault_diagnosis"],
        eligible_zones=["Central"],
        shift_start_min=480,
        shift_end_min=960,
    )
    e2 = Electrician(
        technician_id="E2",
        skills=["fault_diagnosis"],
        eligible_zones=["Central"],
        shift_start_min=480,
        shift_end_min=960,
    )
    j1 = Job(
        job_id="J1",
        required_skills=["fault_diagnosis"],
        priority="Normal",
        duration_min=60,
        zone="Central",
        window_start_min=540,
        window_end_min=660,
        sla_deadline_min=840,
    )
    j2 = Job(
        job_id="J2",
        required_skills=["fault_diagnosis"],
        priority="Normal",
        duration_min=60,
        zone="Central",
        window_start_min=540,
        window_end_min=660,
        sla_deadline_min=840,
    )
    tt_entries = _complete_travel(
        {
            ("HOME_E1", "J1"): 45,
            ("HOME_E1", "J2"): 5,
            ("HOME_E2", "J1"): 5,
            ("HOME_E2", "J2"): 45,
        },
        ["HOME_E1", "HOME_E2", "J1", "J2"],
    )
    t_matrix = TravelMatrix(entries=tt_entries)
    rj1, _ = validate_job_data(j1, SchedulerConfig())
    rj2, _ = validate_job_data(j2, SchedulerConfig())
    assert rj1 is not None and rj2 is not None
    r_e1, _ = build_timed_route(e1, [StopSpec(job=rj1)], [], t_matrix, SchedulerConfig())
    r_e2, _ = build_timed_route(e2, [StopSpec(job=rj2)], [], t_matrix, SchedulerConfig())
    assert r_e1 is not None and r_e2 is not None
    init_sig = compute_schedule_signature({"E1": r_e1, "E2": r_e2})

    def reject_all_candidates(*args, **kwargs):
        routes = kwargs.get("routes_by_tech") if "routes_by_tech" in kwargs else args[0]
        if compute_schedule_signature(routes) == init_sig:
            return real_validate(*args, **kwargs)
        return FullScheduleValidationResult(
            is_valid=False,
            hard_violation_count=1,
            errors=["Simulated full-schedule validation failure"],
        )

    monkeypatch.setattr(opt_mod, "validate_full_schedule", reject_all_candidates)
    blocked_outcome = run_bounded_local_search(
        initial_routes={"E1": r_e1, "E2": r_e2},
        electricians=[e1, e2],
        active_jobs_by_id={"J1": rj1, "J2": rj2},
        unavailability_by_tech={},
        existing_assignments=[],
        travel_matrix=t_matrix,
        config=SchedulerConfig(),
    )
    assert blocked_outcome.moves_evaluated >= 1
    assert blocked_outcome.moves_accepted == 0
    assert compute_schedule_signature(blocked_outcome.routes_by_tech) == init_sig



