"""Unit tests for priority ordering, urgency formula, and scarcity protection (Section 15)."""

from __future__ import annotations

import pytest

from app.scheduler.constraints import validate_job_data
from app.scheduler.engine import generate_schedule
from app.scheduler.prioritization import (
    build_job_priority_profile,
    compute_soft_sla_urgency,
    sort_jobs_by_policy,
)
from app.schemas.scheduling import (
    Electrician,
    Job,
    PriorityLevel,
    SchedulerConfig,
    TravelEntry,
    normalize_priority,
)


@pytest.mark.parametrize(
    ("slack_min", "expected_urgency"),
    [
        (300, 0.0),
        (240, 0.0),
        (180, 25.0),
        (120, 50.0),
        (60, 75.0),
        (0, 100.0),
        (-30, 100.0),
    ],
)
def test_urgency_formula_exact_table_values(slack_min: int, expected_urgency: float) -> None:
    assert compute_soft_sla_urgency(slack_min, horizon_min=240.0) == pytest.approx(expected_urgency)


def test_priority_mapping_and_strict_ordering() -> None:
    assert normalize_priority("P1 Critical") == PriorityLevel.CRITICAL
    assert normalize_priority("High") == PriorityLevel.HIGH
    assert normalize_priority("Normal") == PriorityLevel.NORMAL
    assert normalize_priority("P3 Medium") == PriorityLevel.NORMAL
    assert normalize_priority("P4 Low") == PriorityLevel.LOW

    cfg = SchedulerConfig()
    jobs_raw = [
        Job(job_id="J_LOW_URGENT", priority="Low", duration_min=60, zone="Central", window_start_min=540, window_end_min=600, sla_deadline_min=600),
        Job(job_id="J_CRIT_RELAXED", priority="Critical", duration_min=30, zone="Central", window_start_min=540, window_end_min=600, sla_deadline_min=960),
        Job(job_id="J_NORM", priority="Normal", duration_min=45, zone="Central", window_start_min=540, window_end_min=600, sla_deadline_min=660),
        Job(job_id="J_HIGH", priority="High", duration_min=45, zone="Central", window_start_min=540, window_end_min=600, sla_deadline_min=720),
    ]
    profiles = []
    for j in jobs_raw:
        rj, _ = validate_job_data(j, cfg)
        assert rj is not None
        slack = rj.sla_deadline_min - (rj.window_start_min + rj.duration_min)
        profiles.append(
            build_job_priority_profile(
                job=rj,
                eligible_electrician_count=3,
                feasible_electrician_count=3,
                feasible_slot_count=3,
                best_slack_min=slack,
                horizon_min=240.0,
            )
        )

    ordered = [p.job_id for p in sort_jobs_by_policy(profiles)]
    # Low-priority job with urgency=100 NEVER outranks Critical (urgency=0), High, or Normal
    assert ordered == ["J_CRIT_RELAXED", "J_HIGH", "J_NORM", "J_LOW_URGENT"]


def test_low_priority_never_displaces_critical_on_single_slot() -> None:
    elec = Electrician(
        technician_id="E1",
        skills=["fault_diagnosis"],
        eligible_zones=["Central"],
        shift_start_min=540,
        shift_end_min=660,
    )
    # Only one 60-min job can fit in [540, 660] with 15-min travel
    j_low = Job(
        job_id="J_LOW",
        required_skills=["fault_diagnosis"],
        priority="Low",
        duration_min=60,
        zone="Central",
        window_start_min=555,
        window_end_min=570,
        sla_deadline_min=615,  # Slack = 0 -> urgency 100
    )
    j_crit = Job(
        job_id="J_CRIT",
        required_skills=["fault_diagnosis"],
        priority="Critical",
        duration_min=60,
        zone="Central",
        window_start_min=555,
        window_end_min=570,
        sla_deadline_min=900,  # Slack = 285 -> urgency 0
    )
    tt = [
        TravelEntry(from_location_id="HOME_E1", to_location_id="J_LOW", travel_time_min=15),
        TravelEntry(from_location_id="HOME_E1", to_location_id="J_CRIT", travel_time_min=15),
        TravelEntry(from_location_id="J_LOW", to_location_id="J_CRIT", travel_time_min=15),
        TravelEntry(from_location_id="J_CRIT", to_location_id="J_LOW", travel_time_min=15),
    ]
    res = generate_schedule(jobs=[j_low, j_crit], electricians=[elec], travel_times=tt)
    assert res.assigned_job_ids == ["J_CRIT"]
    assert res.unassigned_job_ids == ["J_LOW"]


def test_scarcity_protection_preserves_specialist_for_constrained_job() -> None:
    # E_SPEC has both general & specialist skill; E_GEN has only general skill
    e_spec = Electrician(
        technician_id="E_SPEC",
        skills=["fault_diagnosis", "ev_charger_installation"],
        eligible_zones=["South"],
        shift_start_min=540,
        shift_end_min=660,
    )
    e_gen = Electrician(
        technician_id="E_GEN",
        skills=["fault_diagnosis"],
        eligible_zones=["South"],
        shift_start_min=540,
        shift_end_min=660,
    )
    # J_FLEX can use E_SPEC or E_GEN and has higher urgency; J_SCARCE can ONLY use E_SPEC!
    j_flex = Job(
        job_id="J_FLEX",
        required_skills=["fault_diagnosis"],
        priority="Normal",
        duration_min=60,
        zone="South",
        window_start_min=555,
        window_end_min=580,
        sla_deadline_min=620,
    )
    j_scarce = Job(
        job_id="J_SCARCE",
        required_skills=["ev_charger_installation"],
        priority="Normal",
        duration_min=60,
        zone="South",
        window_start_min=555,
        window_end_min=580,
        sla_deadline_min=780,
    )
    locs = ["HOME_E_SPEC", "HOME_E_GEN", "J_FLEX", "J_SCARCE"]
    tt = [
        TravelEntry(from_location_id=u, to_location_id=v, travel_time_min=15)
        for u in locs
        for v in locs
    ]
    res = generate_schedule(
        jobs=[j_flex, j_scarce],
        electricians=[e_spec, e_gen],
        travel_times=tt,
        config=SchedulerConfig(enable_optimization=False),  # Even greedy preserves E_SPEC!
    )
    assert set(res.assigned_job_ids) == {"J_FLEX", "J_SCARCE"}
    by_job = {a.job_id: a.technician_id for a in res.final_schedule.assignments}
    assert by_job["J_SCARCE"] == "E_SPEC"
    assert by_job["J_FLEX"] == "E_GEN"


def test_deterministic_tie_breaking_by_job_id() -> None:
    cfg = SchedulerConfig()
    j_b, _ = validate_job_data(
        Job(job_id="J002", priority="Normal", duration_min=60, zone="North", window_start_min=600, window_end_min=700, sla_deadline_min=720),
        cfg,
    )
    j_a, _ = validate_job_data(
        Job(job_id="J001", priority="Normal", duration_min=60, zone="North", window_start_min=600, window_end_min=700, sla_deadline_min=720),
        cfg,
    )
    assert j_a is not None and j_b is not None
    p_b = build_job_priority_profile(j_b, 2, 2, 2, 60)
    p_a = build_job_priority_profile(j_a, 2, 2, 2, 60)
    ordered = sort_jobs_by_policy([p_b, p_a])
    assert [p.job_id for p in ordered] == ["J001", "J002"]

