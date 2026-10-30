"""Dataset loading, feasibility audit, scenario D01/D02, and full validator tests (Section 15)."""

from __future__ import annotations

from pathlib import Path

from app.scheduler.constraints import (
    RouteStop,
    validate_full_schedule,
    validate_job_data,
)
from app.scheduler.dataset_loader import (
    EXPECTED_DATASET_FILES,
    generate_dataset_audit,
    load_dataset_bundle,
)
from app.scheduler.engine import generate_schedule
from app.scheduler.objective import is_strictly_better_objective
from app.scheduler.travel import TravelMatrix
from app.schemas.scheduling import ExistingAssignment, ReasonCode, SchedulerConfig


def test_all_supplied_dataset_files_load_cleanly() -> None:
    bundle = load_dataset_bundle()
    assert bundle.missing_files == []
    assert bundle.malformed_records == []
    assert len(bundle.electricians) == 20
    assert len(bundle.jobs) == 100
    assert len(bundle.travel_entries) == 14400
    assert len(bundle.all_unavailability) == 2
    assert len(bundle.scenarios) == 7
    # Baseline schedule should not activate D01/D02 unavailability or scenario job J101
    assert bundle.unavailability == []
    assert all(j.job_id != "J101" for j in bundle.jobs)


def test_missing_or_malformed_csv_reported_transparently(tmp_path: Path) -> None:
    # Missing files in empty directory are reported without raising unhandled crash
    empty_bundle = load_dataset_bundle(data_dir=tmp_path)
    assert set(empty_bundle.missing_files) == set(EXPECTED_DATASET_FILES)

    # Malformed integer row in electrical_jobs.csv is captured in malformed_records
    bad_jobs_csv = tmp_path / "electrical_jobs.csv"
    bad_jobs_csv.write_text(
        "job_id,trade,job_type,required_skills,priority,duration_min,zone,location_x_km,location_y_km,window_start_min,window_end_min,sla_deadline_min,status,notes\n"
        "J_BAD,electrician,fault_diagnosis,fault_diagnosis,Normal,NOT_AN_INT,Central,1.0,2.0,540,660,720,pending,broken\n"
        "J_GOOD,electrician,fault_diagnosis,fault_diagnosis,Normal,60,Central,1.0,2.0,540,660,720,pending,ok\n",
        encoding="utf-8",
    )
    corrupt_bundle = load_dataset_bundle(data_dir=tmp_path)
    assert len(corrupt_bundle.jobs) == 1
    assert corrupt_bundle.jobs[0].job_id == "J_GOOD"
    assert any("electrical_jobs.csv:2" in msg for msg in corrupt_bundle.malformed_records)


def test_mandatory_dataset_feasibility_audit_distinguishes_static_and_schedule_feasibility() -> None:
    bundle = load_dataset_bundle()
    audit = generate_dataset_audit(bundle=bundle)

    assert audit.total_electricians == 20
    assert audit.active_electricians == 20
    assert audit.total_jobs == 100
    assert audit.missing_baseline_travel_pairs == []
    assert audit.invalid_travel_entries == []
    assert "J101" in audit.scenario_locations_missing_from_matrix

    # Static eligibility: 99 eligible (9 with 1 tech, 90 with 2+ techs), 1 ineligible (J100)
    assert audit.static_eligibility_buckets == {"0": 1, "1": 9, "2+": 90}
    assert "high_voltage_authorization" in audit.unmatched_job_skills
    assert "Remote_Unserved" in audit.unserved_job_zones

    # Isolated schedule feasibility under hard SLA is strictly tighter than static eligibility
    assert audit.isolated_feasibility_buckets_hard_sla["0"] > audit.static_eligibility_buckets["0"]
    assert audit.jobs_with_multiple_feasible_alternatives_hard_sla > 50

    # J012 is statically eligible (2 techs) yet isolated-infeasible due to shift overrun
    infeas_soft_ids = {entry.job_id for entry in audit.isolated_infeasible_jobs_soft_sla}
    assert "J012" in infeas_soft_ids
    assert "J100" in infeas_soft_ids


def test_infeasible_edge_case_detected_by_constraints_not_hardcoded_job_id() -> None:
    bundle = load_dataset_bundle()
    # Rename J100 to an arbitrary identifier and remap its travel entries to prove zero ID hardcoding
    renamed_jobs = []
    for j in bundle.jobs:
        if j.job_id == "J100":
            renamed_jobs.append(
                j.model_copy(update={"job_id": "J_ARBITRARY_EDGE", "location_id": "J100"})
            )
        else:
            renamed_jobs.append(j)

    res = generate_schedule(
        jobs=renamed_jobs,
        electricians=bundle.electricians,
        travel_times=bundle.travel_entries,
        config=SchedulerConfig(enable_optimization=False),
    )
    assert "J_ARBITRARY_EDGE" in res.unassigned_job_ids
    rep = res.unassigned_reasons["J_ARBITRARY_EDGE"]
    assert not rep.is_statically_eligible
    assert rep.static_eligible_count == 0
    assert rep.primary_reason_code in (ReasonCode.MISSING_SKILL, ReasonCode.ZONE_INELIGIBLE)
    assert any("high_voltage_authorization" in d for d in rep.supporting_details)
    assert any("Remote_Unserved" in d for d in rep.supporting_details)


def test_urgent_job_enters_through_scenario_d02_and_d01_recovery_preserves_invariants() -> None:
    base_bundle = load_dataset_bundle()
    base_res = generate_schedule(
        jobs=base_bundle.jobs,
        electricians=base_bundle.electricians,
        travel_times=base_bundle.travel_entries,
        include_dataset_audit=True,
        dataset_bundle=base_bundle,
    )
    assert base_res.is_valid_for_commitment
    assert base_res.final_schedule.hard_constraint_violation_count == 0
    assert len(base_res.final_schedule.assigned_job_ids) >= len(
        base_res.initial_greedy_schedule.assigned_job_ids
    )
    if base_res.optimization.improved:
        assert is_strictly_better_objective(
            base_res.final_schedule.objective,
            base_res.initial_greedy_schedule.objective,
        )

    # Every unassigned job must have an evidence-based explanation
    for u_jid in base_res.unassigned_job_ids:
        assert u_jid in base_res.unassigned_reasons
        assert base_res.unassigned_reasons[u_jid].summary

    # Independently re-verify every final assignment through full hard-constraint validator
    cfg = base_res.config
    elecs_by_id = {e.technician_id: e for e in base_bundle.electricians}
    valid_jobs = {}
    for j in base_bundle.jobs:
        rj, _ = validate_job_data(j, cfg)
        if rj is not None:
            valid_jobs[j.job_id] = rj

    reconstructed_routes: dict[str, list[RouteStop]] = {
        e.technician_id: [] for e in base_bundle.electricians
    }
    for a in base_res.final_schedule.assignments:
        reconstructed_routes[a.technician_id].append(
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
    t_mat = TravelMatrix(
        entries=base_bundle.travel_entries,
        electricians=base_bundle.electricians,
        jobs=base_bundle.jobs,
    )
    full_check = validate_full_schedule(
        routes_by_tech=reconstructed_routes,
        electricians_by_id=elecs_by_id,
        valid_jobs_by_id=valid_jobs,
        unavailability_by_tech={},
        existing_assignments=[],
        travel_matrix=t_mat,
        config=cfg,
    )
    assert full_check.is_valid
    assert full_check.hard_violation_count == 0

    # Trigger Scenario D02: J101 arrives dynamically and E011 has safety training [600, 690]
    d02_bundle = load_dataset_bundle(scenario_ids=["D02"])
    assert any(j.job_id == "J101" for j in d02_bundle.jobs)
    prior_commitments = [
        ExistingAssignment(
            job_id=a.job_id,
            technician_id=a.technician_id,
            departure_min=a.departure_min,
            arrival_min=a.arrival_min,
            planned_start_min=a.planned_start_min,
            completion_min=a.completion_min,
            status="completed" if a.completion_min <= 630 else "assigned",
            locked=(a.completion_min <= 630),
        )
        for a in base_res.final_schedule.assignments
    ]
    d02_res = generate_schedule(
        jobs=d02_bundle.jobs,
        electricians=d02_bundle.electricians,
        travel_times=d02_bundle.travel_entries,
        existing_assignments=prior_commitments,
        unavailability=d02_bundle.unavailability,
        active_scenario_ids=["D02"],
    )
    assert d02_res.is_valid_for_commitment
    assert "J101" in d02_res.assigned_job_ids
    # All completed jobs before t=630 remained strictly fixed
    d02_by_job = {a.job_id: a for a in d02_res.final_schedule.assignments}
    for ex in prior_commitments:
        if ex.locked:
            assert d02_by_job[ex.job_id].technician_id == ex.technician_id
            assert d02_by_job[ex.job_id].planned_start_min == ex.planned_start_min


def test_disruption_recovery_invariants_d01_d04_d05() -> None:
    base_bundle = load_dataset_bundle()
    base_res = generate_schedule(
        jobs=base_bundle.jobs,
        electricians=base_bundle.electricians,
        travel_times=base_bundle.travel_entries,
    )

    # D01: E004 unavailable [720, 1020]; D04: J027 cancelled; D05: J009 completed
    d01_bundle = load_dataset_bundle(scenario_ids=["D01", "D04", "D05"])
    prior: list[ExistingAssignment] = []
    for a in base_res.final_schedule.assignments:
        st = "completed" if a.job_id == "J009" or a.completion_min <= 615 else "assigned"
        prior.append(
            ExistingAssignment(
                job_id=a.job_id,
                technician_id=a.technician_id,
                departure_min=a.departure_min,
                arrival_min=a.arrival_min,
                planned_start_min=a.planned_start_min,
                completion_min=a.completion_min,
                status=st,
                locked=(st == "completed"),
            )
        )

    rec_res = generate_schedule(
        jobs=d01_bundle.jobs,
        electricians=d01_bundle.electricians,
        travel_times=d01_bundle.travel_entries,
        existing_assignments=prior,
        unavailability=d01_bundle.unavailability,
        active_scenario_ids=["D01", "D04", "D05"],
    )
    assert rec_res.is_valid_for_commitment
    assert rec_res.final_schedule.hard_constraint_violation_count == 0
    # J027 was cancelled -> does not consume capacity
    assert "J027" not in rec_res.assigned_job_ids
    assert "J027" not in rec_res.unassigned_job_ids
    # E004 has zero unlocked jobs overlapping [720, 1020]
    for a in rec_res.final_schedule.assignments:
        if a.technician_id == "E004" and not a.is_protected:
            assert a.completion_min <= 720 or a.departure_min >= 1020
    # Completed J009 remained fixed on its baseline technician and start time
    base_j009 = next(a for a in base_res.final_schedule.assignments if a.job_id == "J009")
    rec_j009 = next(a for a in rec_res.final_schedule.assignments if a.job_id == "J009")
    assert rec_j009.technician_id == base_j009.technician_id
    assert rec_j009.planned_start_min == base_j009.planned_start_min

