"""Regression tests for all 7 disruption scenarios (D01-D07), protected commitments, and idempotency."""

from __future__ import annotations

import pytest

from app.scheduler.dataset_loader import load_dataset_bundle
from app.scheduler.recovery import (
    IdempotencyConflictError,
    IdempotentRequestRegistry,
    get_scenario_specifications,
    simulate_all_scenarios,
    simulate_scenario,
    submit_idempotent_job,
)
from app.schemas.dispatch_recovery import RecoveryActionType
from app.schemas.scheduling import ReasonCode, SchedulerConfig


EXPECTED_SCENARIOS = ["D01", "D02", "D03", "D04", "D05", "D06", "D07"]


def test_all_seven_scenario_specifications_complete() -> None:
    specs = get_scenario_specifications()
    assert sorted(specs.keys()) == EXPECTED_SCENARIOS

    for sid in EXPECTED_SCENARIOS:
        spec = specs[sid]
        assert spec.scenario_id == sid
        assert spec.trigger_description
        assert len(spec.expected_affected_entities) >= 1
        assert spec.expected_recovery_action
        assert len(spec.enforced_constraints) >= 5
        assert spec.expected_outcome


def test_d01_technician_unavailable_evicts_future_and_preserves_completed_and_in_progress() -> None:
    # 1. Default strict hard SLA: E004's completed stops (<= 720) remain fixed; future stop J054 (720) is reassigned
    res_hard = simulate_scenario("D01", config=SchedulerConfig(sla_mode="hard"))
    assert res_hard.validation_passed is True
    assert res_hard.objective_consistent is True
    assert res_hard.recovered_schedule_run.is_valid_for_commitment is True

    e004_stops_hard = [
        a
        for a in res_hard.recovered_schedule_run.final_schedule.assignments
        if a.technician_id == "E004"
    ]
    for stop in e004_stops_hard:
        # E004 is unavailable [720, 1020); only historical completed stops <= 720 may remain on E004
        assert stop.status == "completed"
        assert stop.completion_min <= 720
    assert "J054" in res_hard.reassigned_job_ids
    assert res_hard.job_recovery_explanations["J054"].action_type == RecoveryActionType.REASSIGNED_TECHNICIAN

    # 2. hard_critical_only: E004 has active in-progress job J056 (start=700 < 720 < comp=775) + future J080 (785)
    res_crit = simulate_scenario("D01", config=SchedulerConfig(sla_mode="hard_critical_only"))
    assert res_crit.validation_passed is True
    assert res_crit.objective_consistent is True
    assert "J056" in res_crit.preserved_in_progress_job_ids
    e004_stops_crit = {
        a.job_id: a
        for a in res_crit.recovered_schedule_run.final_schedule.assignments
        if a.technician_id == "E004"
    }
    assert "J056" in e004_stops_crit
    assert e004_stops_crit["J056"].status == "in_progress"
    assert "J080" not in e004_stops_crit
    assert "J080" in res_crit.affected_job_ids
    assert res_crit.job_recovery_explanations["J080"].action_type in (
        RecoveryActionType.REASSIGNED_TECHNICIAN,
        RecoveryActionType.UNASSIGNED_AFTER_DISRUPTION,
    )


def test_d02_urgent_job_arrival_j101_inserted_within_hard_sla_and_u002_enforced() -> None:
    res = simulate_scenario("D02")
    assert res.validation_passed is True
    assert res.objective_consistent is True
    assert "J101" in res.recovered_schedule_run.assigned_job_ids
    assert "J101" in res.newly_assigned_job_ids

    j101_asgn = next(
        a for a in res.recovered_schedule_run.final_schedule.assignments if a.job_id == "J101"
    )
    assert 630 <= j101_asgn.planned_start_min <= 750
    assert j101_asgn.completion_min <= 720
    assert res.job_recovery_explanations["J101"].action_type == RecoveryActionType.NEWLY_INSERTED_URGENT

    # Verify E011 respects scenario unavailability U002 [600, 690) for all non-historical stops
    for a in res.recovered_schedule_run.final_schedule.assignments:
        if a.technician_id == "E011" and a.status not in ("completed", "in_progress"):
            assert a.completion_min <= 600 or a.departure_min >= 690


def test_d03_duration_overrun_j018_under_hard_sla_and_active_in_progress_mode() -> None:
    # 1. Under strict hard SLA: J018 (window_start=480 + duration=195 = 675 > sla=600) is infeasible -> cleanly unassigned
    res_hard = simulate_scenario("D03", config=SchedulerConfig(sla_mode="hard"))
    assert res_hard.validation_passed is True
    assert res_hard.objective_consistent is True
    assert "J018" in res_hard.recovered_schedule_run.unassigned_job_ids
    j018_rep = res_hard.recovered_schedule_run.unassigned_reasons["J018"]
    assert j018_rep.primary_reason_code == ReasonCode.SLA_DEADLINE_INFEASIBLE
    assert res_hard.job_recovery_explanations["J018"].action_type == RecoveryActionType.LEFT_UNASSIGNED

    # 2. Under hard_critical_only: J018 is actively in progress at t=660 -> protected start, +45m completion, valid cascade
    res_active = simulate_scenario("D03", config=SchedulerConfig(sla_mode="hard_critical_only"))
    assert res_active.validation_passed is True
    assert res_active.objective_consistent is True
    assert "J018" in res_active.preserved_in_progress_job_ids
    j018_expl = res_active.job_recovery_explanations["J018"]
    assert j018_expl.action_type == RecoveryActionType.DURATION_EXTENDED_IN_PROGRESS
    assert j018_expl.previous_technician_id == j018_expl.new_technician_id
    assert j018_expl.previous_start_min == j018_expl.new_start_min
    assert (j018_expl.new_completion_min or 0) - (j018_expl.previous_completion_min or 0) == 45


def test_d04_job_cancelled_j027_removed_and_capacity_reclaimed() -> None:
    res = simulate_scenario("D04")
    assert res.validation_passed is True
    assert res.objective_consistent is True
    assert res.cancelled_job_ids == ["J027"]
    assert "J027" not in res.recovered_schedule_run.assigned_job_ids
    assert "J027" not in res.recovered_schedule_run.unassigned_job_ids
    assert res.job_recovery_explanations["J027"].action_type == RecoveryActionType.CANCELLED_REMOVED


def test_d05_job_completed_j009_remains_permanently_anchored() -> None:
    res = simulate_scenario("D05")
    assert res.validation_passed is True
    assert res.objective_consistent is True
    assert "J009" in res.preserved_completed_job_ids

    j009_asgn = next(
        a for a in res.recovered_schedule_run.final_schedule.assignments if a.job_id == "J009"
    )
    assert j009_asgn.technician_id == "E004"
    assert j009_asgn.planned_start_min == 600
    assert j009_asgn.status == "completed"
    assert j009_asgn.is_protected is True
    assert res.job_recovery_explanations["J009"].action_type == RecoveryActionType.PRESERVED_COMPLETED


def test_d06_duplicate_request_j033_suppressed_and_idempotency_conflict_rejected() -> None:
    res = simulate_scenario("D06")
    assert res.validation_passed is True
    assert res.objective_consistent is True
    assert res.duplicate_request_suppressed is True
    assert res.job_recovery_explanations["J033"].action_type == RecoveryActionType.DEDUPLICATED_REQUEST
    # J033 appears at most once across assigned + unassigned
    total_j033_occurrences = (
        res.recovered_schedule_run.assigned_job_ids.count("J033")
        + res.recovered_schedule_run.unassigned_job_ids.count("J033")
    )
    assert total_j033_occurrences == 1

    # Direct IdempotentRequestRegistry + submit_idempotent_job verification
    bundle = load_dataset_bundle()
    j033 = next(j for j in bundle.jobs if j.job_id == "J033")
    registry = IdempotentRequestRegistry()

    sub1 = submit_idempotent_job(
        idempotency_key="idem-j033-req-001",
        job=j033,
        registry=registry,
        event_time_min=540,
        config=SchedulerConfig(enable_optimization=False),
    )
    assert sub1.created is True
    assert sub1.duplicate_suppressed is False
    assert sub1.schedule_run is not None

    sub2 = submit_idempotent_job(
        idempotency_key="idem-j033-req-001",
        job=j033,
        registry=registry,
        event_time_min=540,
        config=SchedulerConfig(enable_optimization=False),
    )
    assert sub2.created is False
    assert sub2.duplicate_suppressed is True
    assert sub2.schedule_run is not None
    assert sub2.schedule_run.run_id == sub1.schedule_run.run_id

    # Reusing the same idempotency_key with a mutated payload must raise IdempotencyConflictError
    mutated_j033 = j033.model_copy(update={"duration_min": j033.duration_min + 30})
    with pytest.raises(IdempotencyConflictError):
        submit_idempotent_job(
            idempotency_key="idem-j033-req-001",
            job=mutated_j033,
            registry=registry,
            event_time_min=540,
            config=SchedulerConfig(enable_optimization=False),
        )


def test_d07_unassignable_job_j100_leaves_schedule_intact_with_grounded_reasons() -> None:
    res = simulate_scenario("D07")
    assert res.validation_passed is True
    assert res.objective_consistent is True
    assert "J100" not in res.recovered_schedule_run.assigned_job_ids
    assert "J100" in res.recovered_schedule_run.unassigned_job_ids

    rep = res.recovered_schedule_run.unassigned_reasons["J100"]
    assert rep.is_statically_eligible is False
    assert rep.static_eligible_count == 0
    assert rep.primary_reason_code == ReasonCode.MISSING_SKILL
    assert any("Remote_Unserved" in d for d in rep.supporting_details)

    j100_expl = res.job_recovery_explanations["J100"]
    assert j100_expl.action_type == RecoveryActionType.LEFT_UNASSIGNED
    assert len(j100_expl.rejected_candidates) >= 1


def test_locked_future_assignment_preserved_during_disruption_recovery() -> None:
    # First obtain baseline for D04 (event_time_min=600) and pick a future unlocked stop (> 600, != J027)
    probe = simulate_scenario("D04", config=SchedulerConfig(enable_optimization=False))
    future_candidates = [
        a
        for a in probe.recovered_schedule_run.final_schedule.assignments
        if a.planned_start_min > 660 and not a.is_protected
    ]
    assert future_candidates, "Expected at least one future scheduled stop after 660"
    locked_target = future_candidates[0].job_id

    res_locked = simulate_scenario(
        "D04",
        locked_future_job_ids=[locked_target],
    )
    assert res_locked.validation_passed is True
    assert res_locked.objective_consistent is True
    assert locked_target in res_locked.preserved_locked_future_job_ids
    assert (
        res_locked.job_recovery_explanations[locked_target].action_type
        == RecoveryActionType.PRESERVED_LOCKED_FUTURE
    )
    locked_asgn = next(
        a
        for a in res_locked.recovered_schedule_run.final_schedule.assignments
        if a.job_id == locked_target
    )
    assert locked_asgn.is_protected is True


def test_simulate_all_scenarios_reproducible_valid_and_objective_consistent() -> None:
    suite_1 = simulate_all_scenarios()
    suite_2 = simulate_all_scenarios()

    assert sorted(suite_1.results_by_scenario.keys()) == EXPECTED_SCENARIOS
    assert suite_1.all_validations_passed is True
    assert suite_1.all_objectives_consistent is True

    for sid in EXPECTED_SCENARIOS:
        r1 = suite_1.results_by_scenario[sid]
        r2 = suite_2.results_by_scenario[sid]
        assert r1.validation_passed is True
        assert r1.validation_errors == []
        assert r1.objective_consistent is True
        assert r1.recovered_schedule_run.assigned_job_ids == r2.recovered_schedule_run.assigned_job_ids
        assert r1.recovered_schedule_run.unassigned_job_ids == r2.recovered_schedule_run.unassigned_job_ids
        assert (
            r1.recovered_schedule_run.final_schedule.objective
            == r2.recovered_schedule_run.final_schedule.objective
        )

