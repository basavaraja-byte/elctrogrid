"""Unit tests for the Initial Greedy Scheduler, route insertion cost, and metrics (Section 15)."""

from __future__ import annotations

import pytest

from app.scheduler.engine import generate_schedule
from app.schemas.scheduling import (
    Electrician,
    ExistingAssignment,
    Job,
    ReasonCode,
    SchedulerConfig,
    TravelEntry,
)


def test_greedy_scheduler_assigns_feasible_and_explains_infeasible() -> None:
    elecs = [
        Electrician(
            technician_id="E1",
            skills=["fault_diagnosis", "residential_wiring"],
            eligible_zones=["Central"],
            shift_start_min=480,
            shift_end_min=960,
        )
    ]
    jobs = [
        Job(
            job_id="J_OK_1",
            required_skills=["fault_diagnosis"],
            priority="High",
            duration_min=60,
            zone="Central",
            window_start_min=540,
            window_end_min=600,
            sla_deadline_min=660,
        ),
        Job(
            job_id="J_OK_2",
            required_skills=["residential_wiring"],
            priority="Normal",
            duration_min=90,
            zone="Central",
            window_start_min=660,
            window_end_min=720,
            sla_deadline_min=840,
        ),
        Job(
            job_id="J_UNSERVED",
            required_skills=["commercial_wiring"],
            priority="Low",
            duration_min=60,
            zone="Central",
            window_start_min=780,
            window_end_min=840,
            sla_deadline_min=900,
        ),
    ]
    locs = ["HOME_E1", "J_OK_1", "J_OK_2", "J_UNSERVED"]
    tt = [
        TravelEntry(from_location_id=u, to_location_id=v, travel_time_min=0 if u == v else 20)
        for u in locs
        for v in locs
    ]

    res = generate_schedule(
        jobs=jobs,
        electricians=elecs,
        travel_times=tt,
        config=SchedulerConfig(enable_optimization=False),
    )
    assert res.is_valid_for_commitment
    assert res.initial_greedy_schedule.hard_constraint_violation_count == 0
    assert res.assigned_job_ids == ["J_OK_1", "J_OK_2"]
    assert res.unassigned_job_ids == ["J_UNSERVED"]
    assert res.unassigned_reasons["J_UNSERVED"].primary_reason_code == ReasonCode.MISSING_SKILL
    assert "J_OK_1" in res.explanations
    assert "J_OK_2" in res.explanations


def test_route_insertion_accounts_for_predecessor_and_successor_legs() -> None:
    elec = Electrician(
        technician_id="E1",
        skills=["fault_diagnosis"],
        eligible_zones=["Central"],
        shift_start_min=480,
        shift_end_min=960,
    )
    # J_LATE is Critical (scheduled first at 720), J_MID is Normal (inserted BEFORE J_LATE at 560)
    j_late = Job(
        job_id="J_LATE",
        required_skills=["fault_diagnosis"],
        priority="Critical",
        duration_min=60,
        zone="Central",
        window_start_min=720,
        window_end_min=780,
        sla_deadline_min=840,
    )
    j_mid = Job(
        job_id="J_MID",
        required_skills=["fault_diagnosis"],
        priority="Normal",
        duration_min=60,
        zone="Central",
        window_start_min=540,
        window_end_min=600,
        sla_deadline_min=660,
    )
    # HOME_E1 -> J_LATE directly is 30 min; HOME_E1 -> J_MID is 15 min, J_MID -> J_LATE is 20 min
    # Inserting J_MID at pos 0 replaces leg HOME->J_LATE (30) with HOME->J_MID (15) + J_MID->J_LATE (20) => +5 incremental!
    tt = [
        TravelEntry(from_location_id="HOME_E1", to_location_id="J_LATE", travel_time_min=30),
        TravelEntry(from_location_id="HOME_E1", to_location_id="J_MID", travel_time_min=15),
        TravelEntry(from_location_id="J_MID", to_location_id="J_LATE", travel_time_min=20),
        TravelEntry(from_location_id="J_LATE", to_location_id="J_MID", travel_time_min=20),
    ]
    res = generate_schedule(
        jobs=[j_late, j_mid],
        electricians=[elec],
        travel_times=tt,
        config=SchedulerConfig(enable_optimization=False),
    )
    assert res.final_schedule.total_travel_min == 35
    by_job = {a.job_id: a for a in res.final_schedule.assignments}
    assert by_job["J_MID"].route_position == 0
    assert by_job["J_MID"].incremental_travel_min == 5
    assert by_job["J_LATE"].route_position == 1


def test_separate_service_and_travel_workloads_and_zero_initial_change_cost() -> None:
    elec = Electrician(
        technician_id="E1",
        skills=["fault_diagnosis"],
        eligible_zones=["Central"],
        shift_start_min=480,
        shift_end_min=960,
    )
    job = Job(
        job_id="J1",
        required_skills=["fault_diagnosis"],
        priority="High",
        duration_min=75,
        zone="Central",
        window_start_min=540,
        window_end_min=600,
        sla_deadline_min=720,
    )
    tt = [TravelEntry(from_location_id="HOME_E1", to_location_id="J1", travel_time_min=25)]
    res = generate_schedule(jobs=[job], electricians=[elec], travel_times=tt)

    wk = res.final_schedule.technician_workloads[0]
    assert wk.planned_service_min == 75
    assert wk.planned_travel_min == 25
    assert wk.total_duty_min == 100
    assert wk.service_utilization == pytest.approx(75 / 480.0)
    # Schedule-change cost CR must be 0.0 during initial scheduling
    assert res.final_schedule.objective.schedule_change_cost_norm == 0.0
    assert res.final_schedule.objective.raw_schedule_change_units == 0.0

    # During recovery with a baseline commitment on a different technician, CR > 0
    elec_off = Electrician(
        technician_id="E2",
        skills=["fault_diagnosis"],
        eligible_zones=["Central"],
        shift_start_min=480,
        shift_end_min=960,
        status="inactive",
    )
    res_rec = generate_schedule(
        jobs=[job],
        electricians=[elec, elec_off],
        travel_times=tt + [TravelEntry(from_location_id="HOME_E2", to_location_id="J1", travel_time_min=10)],
        existing_assignments=[
            ExistingAssignment(job_id="J1", technician_id="E2", planned_start_min=540, status="assigned", locked=False)
        ],
    )
    assert res_rec.final_schedule.assignments[0].technician_id == "E1"
    assert res_rec.final_schedule.objective.schedule_change_cost_norm > 0.0

