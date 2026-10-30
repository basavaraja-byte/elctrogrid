"""Unit tests for Module B hard-constraint validation (Section 15)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.scheduler.constraints import (
    RouteStop,
    check_static_eligibility,
    validate_full_schedule,
    validate_job_data,
    validate_route,
)
from app.scheduler.engine import generate_schedule
from app.scheduler.travel import TravelMatrix
from app.schemas.scheduling import (
    Electrician,
    ExistingAssignment,
    Job,
    ReasonCode,
    SchedulerConfig,
    TravelEntry,
    UnavailabilityInterval,
)


def _make_elec(
    tid: str = "E1",
    skills: list[str] | None = None,
    certs: list[str] | None = None,
    zones: list[str] | None = None,
    shift_start: int = 480,
    shift_end: int = 960,
    status: str = "active",
) -> Electrician:
    return Electrician(
        technician_id=tid,
        name=f"Tech {tid}",
        trade="electrician",
        skills=skills if skills is not None else ["fault_diagnosis", "safety_inspection"],
        certifications=certs if certs is not None else ["osha_10"],
        eligible_zones=zones if zones is not None else ["Central", "North"],
        shift_start_min=shift_start,
        shift_end_min=shift_end,
        start_x_km=5.0,
        start_y_km=5.0,
        status=status,
    )


def _make_job(
    jid: str = "J1",
    skills: list[str] | None = None,
    certs: list[str] | None = None,
    zone: str = "Central",
    priority: str = "Normal",
    duration: int = 60,
    ws: int = 540,
    we: int = 720,
    sla: int = 780,
    status: str = "pending",
) -> Job:
    return Job(
        job_id=jid,
        trade="electrician",
        job_type="fault_diagnosis",
        required_skills=skills if skills is not None else ["fault_diagnosis"],
        required_certifications=certs if certs is not None else [],
        priority=priority,
        duration_min=duration,
        zone=zone,
        location_x_km=6.0,
        location_y_km=6.0,
        window_start_min=ws,
        window_end_min=we,
        sla_deadline_min=sla,
        status=status,
    )


def _basic_travel(from_id: str = "HOME_E1", to_id: str = "J1", minutes: int = 15) -> list[TravelEntry]:
    return [
        TravelEntry(from_location_id=from_id, to_location_id=to_id, travel_time_min=minutes),
        TravelEntry(from_location_id=to_id, to_location_id=from_id, travel_time_min=minutes),
    ]


def test_missing_skill_rejected() -> None:
    elec = _make_elec(skills=["safety_inspection"])
    job = _make_job(skills=["ev_charger_installation"])
    res = generate_schedule(
        jobs=[job],
        electricians=[elec],
        travel_times=_basic_travel(),
    )
    assert job.job_id in res.unassigned_job_ids
    assert res.unassigned_reasons[job.job_id].primary_reason_code == ReasonCode.MISSING_SKILL


def test_missing_certification_rejected() -> None:
    elec = _make_elec(skills=["fault_diagnosis"], certs=["osha_10"])
    job = _make_job(skills=["fault_diagnosis"], certs=["high_voltage_license"])
    rjob, errs = validate_job_data(job, SchedulerConfig())
    assert not errs and rjob is not None
    static_errs = check_static_eligibility(rjob, elec)
    assert any(e.code == ReasonCode.MISSING_CERTIFICATION for e in static_errs)

    res = generate_schedule(
        jobs=[job],
        electricians=[elec],
        travel_times=_basic_travel(),
    )
    assert job.job_id in res.unassigned_job_ids
    assert res.unassigned_reasons[job.job_id].primary_reason_code == ReasonCode.MISSING_CERTIFICATION


def test_zone_ineligibility_rejected() -> None:
    elec = _make_elec(zones=["North", "East"])
    job = _make_job(zone="South")
    res = generate_schedule(
        jobs=[job],
        electricians=[elec],
        travel_times=_basic_travel(),
    )
    assert job.job_id in res.unassigned_job_ids
    assert res.unassigned_reasons[job.job_id].primary_reason_code == ReasonCode.ZONE_INELIGIBLE


def test_shift_boundary_violation_and_overtime_policy() -> None:
    elec = _make_elec(shift_start=480, shift_end=900)
    # Earliest start 840 + 90m duration = 930 > shift_end 900
    job = _make_job(ws=840, we=900, duration=90, sla=960)
    res_no_ot = generate_schedule(
        jobs=[job],
        electricians=[elec],
        travel_times=_basic_travel(),
        config=SchedulerConfig(allow_overtime=False),
    )
    assert job.job_id in res_no_ot.unassigned_job_ids
    assert res_no_ot.unassigned_reasons[job.job_id].primary_reason_code == ReasonCode.SHIFT_CONSTRAINT

    # Explicitly enabling 30m overtime makes 930 feasible
    res_ot = generate_schedule(
        jobs=[job],
        electricians=[elec],
        travel_times=_basic_travel(),
        config=SchedulerConfig(allow_overtime=True, max_overtime_min=30),
    )
    assert job.job_id in res_ot.assigned_job_ids
    assert res_ot.final_schedule.technician_workloads[0].overtime_min == 30


def test_technician_unavailability_blocks_and_shifts_slot() -> None:
    elec = _make_elec(shift_start=480, shift_end=960)
    # Unavailability covers entire job window [540, 660]
    job_blocked = _make_job(jid="J_BLK", ws=540, we=600, duration=60, sla=720)
    unavail_full = [
        UnavailabilityInterval(
            unavailability_id="U1",
            technician_id="E1",
            start_min=520,
            end_min=690,
            reason="Training",
        )
    ]
    res_blk = generate_schedule(
        jobs=[job_blocked],
        electricians=[elec],
        travel_times=_basic_travel(to_id="J_BLK", minutes=15),
        unavailability=unavail_full,
    )
    assert "J_BLK" in res_blk.unassigned_job_ids
    assert res_blk.unassigned_reasons["J_BLK"].primary_reason_code == ReasonCode.NO_AVAILABLE_SLOT

    # Wider window [540, 750] allows scheduling right after unavailability ends at 690
    job_shifted = _make_job(jid="J_SHF", ws=540, we=750, duration=60, sla=800)
    res_shf = generate_schedule(
        jobs=[job_shifted],
        electricians=[elec],
        travel_times=_basic_travel(to_id="J_SHF", minutes=15),
        unavailability=unavail_full,
    )
    assert "J_SHF" in res_shf.assigned_job_ids
    asgn = res_shf.final_schedule.assignments[0]
    assert asgn.departure_min >= 690
    assert asgn.planned_start_min == 705
    assert asgn.completion_min == 765


def test_overlapping_assignments_rejected_by_validator() -> None:
    cfg = SchedulerConfig()
    elec = _make_elec()
    j1, _ = validate_job_data(_make_job("J1", ws=500, we=600, duration=60, sla=700), cfg)
    j2, _ = validate_job_data(_make_job("J2", ws=530, we=650, duration=60, sla=720), cfg)
    assert j1 is not None and j2 is not None

    tt = TravelMatrix(
        entries=[
            TravelEntry(from_location_id="HOME_E1", to_location_id="J1", travel_time_min=10),
            TravelEntry(from_location_id="J1", to_location_id="J2", travel_time_min=10),
        ]
    )
    stop1 = RouteStop(
        job=j1,
        technician_id="E1",
        from_location_id="HOME_E1",
        departure_min=490,
        arrival_min=500,
        planned_start_min=500,
        completion_min=560,
        travel_time_min=10,
    )
    # Deliberately overlapping stop2 departing at 540 before stop1 finishes at 560
    stop2 = RouteStop(
        job=j2,
        technician_id="E1",
        from_location_id="J1",
        departure_min=540,
        arrival_min=550,
        planned_start_min=550,
        completion_min=610,
        travel_time_min=10,
    )
    errs = validate_route(elec, [stop1, stop2], [], tt, cfg)
    assert any(e.code == ReasonCode.TRAVEL_CONFLICT for e in errs)

    full_val = validate_full_schedule(
        routes_by_tech={"E1": [stop1, stop2]},
        electricians_by_id={"E1": elec},
        valid_jobs_by_id={"J1": j1, "J2": j2},
        unavailability_by_tech={},
        existing_assignments=[],
        travel_matrix=tt,
        config=cfg,
    )
    assert not full_val.is_valid
    assert full_val.hard_violation_count >= 1


def test_insufficient_travel_time_between_jobs() -> None:
    elec = _make_elec(shift_start=480, shift_end=960)
    j1 = _make_job("J1", priority="Critical", ws=500, we=500, duration=60, sla=600)
    # J1 finishes at 560; J2 requires latest start 580, but travel J1->J2 is 35 min (earliest arrival 595)
    j2 = _make_job("J2", priority="Normal", ws=560, we=580, duration=45, sla=700)
    tt = [
        TravelEntry(from_location_id="HOME_E1", to_location_id="J1", travel_time_min=15),
        TravelEntry(from_location_id="HOME_E1", to_location_id="J2", travel_time_min=15),
        TravelEntry(from_location_id="J1", to_location_id="J2", travel_time_min=35),
        TravelEntry(from_location_id="J2", to_location_id="J1", travel_time_min=35),
    ]
    res = generate_schedule(jobs=[j1, j2], electricians=[elec], travel_times=tt)
    assert "J1" in res.assigned_job_ids
    assert "J2" in res.unassigned_job_ids
    assert res.unassigned_reasons["J2"].primary_reason_code in (
        ReasonCode.TRAVEL_CONFLICT,
        ReasonCode.RESOURCE_CAPACITY_EXHAUSTED,
    )


def test_infeasible_hard_deadline_vs_soft_deadline() -> None:
    elec = _make_elec()
    # Earliest start 600 + 90m duration = 690 > sla_deadline 660
    job = _make_job("J_SLA", ws=600, we=720, duration=90, sla=660)
    res_hard = generate_schedule(
        jobs=[job],
        electricians=[elec],
        travel_times=_basic_travel(to_id="J_SLA"),
        config=SchedulerConfig(sla_mode="hard"),
    )
    assert "J_SLA" in res_hard.unassigned_job_ids
    assert res_hard.unassigned_reasons["J_SLA"].primary_reason_code == ReasonCode.SLA_DEADLINE_INFEASIBLE

    res_soft = generate_schedule(
        jobs=[job],
        electricians=[elec],
        travel_times=_basic_travel(to_id="J_SLA"),
        config=SchedulerConfig(sla_mode="soft"),
    )
    assert "J_SLA" in res_soft.assigned_job_ids
    assert res_soft.final_schedule.predicted_soft_sla_breach_count == 1
    assert res_soft.final_schedule.assignments[0].slack_min == -30


@pytest.mark.parametrize(
    "bad_job",
    [
        _make_job("J_ZERO_DUR", duration=0),
        _make_job("J_NEG_DUR", duration=-30),
        _make_job("J_INV_WIN", ws=700, we=600),
        _make_job("J_BAD_PRIO", priority="SuperUltra"),
        Job(
            job_id="J_NAIVE_DT",
            trade="electrician",
            required_skills=["fault_diagnosis"],
            priority="Normal",
            duration_min=45,
            zone="Central",
            window_start_dt=datetime(2026, 10, 30, 9, 0),  # naive datetime -> invalid!
            window_end_dt=datetime(2026, 10, 30, 11, 0, tzinfo=timezone.utc),
            sla_deadline_dt=datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc),
        ),
    ],
)
def test_invalid_duration_or_timestamp_classified_cleanly(bad_job: Job) -> None:
    elec = _make_elec()
    res = generate_schedule(
        jobs=[bad_job],
        electricians=[elec],
        travel_times=_basic_travel(to_id=bad_job.job_id),
    )
    assert bad_job.job_id in res.unassigned_job_ids
    assert res.unassigned_reasons[bad_job.job_id].primary_reason_code == ReasonCode.INVALID_JOB_DATA


def test_missing_travel_data_never_defaults_to_zero() -> None:
    elec = Electrician(
        technician_id="E1",
        trade="electrician",
        skills=["fault_diagnosis"],
        eligible_zones=["Central"],
        shift_start_min=480,
        shift_end_min=960,
        start_x_km=None,
        start_y_km=None,
    )
    job = Job(
        job_id="J_NO_TT",
        trade="electrician",
        required_skills=["fault_diagnosis"],
        priority="High",
        duration_min=45,
        zone="Central",
        window_start_min=540,
        window_end_min=720,
        sla_deadline_min=780,
    )
    res = generate_schedule(
        jobs=[job],
        electricians=[elec],
        travel_times=[],  # Empty travel matrix & no coordinates
        config=SchedulerConfig(allow_coordinate_travel_fallback=False),
    )
    assert "J_NO_TT" in res.unassigned_job_ids
    assert res.unassigned_reasons["J_NO_TT"].primary_reason_code == ReasonCode.MISSING_TRAVEL_DATA


def test_protected_commitments_and_cancelled_jobs() -> None:
    elec1 = _make_elec("E1")
    elec2 = _make_elec("E2")
    j_done = _make_job("J_DONE", priority="Normal", ws=500, we=600, duration=60, sla=660, status="completed")
    j_prog = _make_job("J_PROG", priority="Normal", ws=620, we=700, duration=75, sla=780, status="in_progress")
    j_canc = _make_job("J_CANC", priority="Critical", ws=500, we=600, duration=60, sla=660, status="cancelled")
    j_crit = _make_job("J_CRIT", priority="Critical", ws=500, we=560, duration=60, sla=660)

    tt = [
        TravelEntry(from_location_id=u, to_location_id=v, travel_time_min=10)
        for u in ("HOME_E1", "HOME_E2", "J_DONE", "J_PROG", "J_CANC", "J_CRIT")
        for v in ("HOME_E1", "HOME_E2", "J_DONE", "J_PROG", "J_CANC", "J_CRIT")
    ]
    existing = [
        ExistingAssignment(job_id="J_DONE", technician_id="E1", planned_start_min=500, status="completed"),
        ExistingAssignment(job_id="J_PROG", technician_id="E1", planned_start_min=630, status="in_progress"),
    ]
    res = generate_schedule(
        jobs=[j_done, j_prog, j_canc, j_crit],
        electricians=[elec1, elec2],
        travel_times=tt,
        existing_assignments=existing,
    )
    assert res.is_valid_for_commitment
    # Cancelled job consumes zero capacity and is excluded
    assert "J_CANC" not in res.assigned_job_ids
    assert "J_CANC" not in res.unassigned_job_ids

    by_job = {a.job_id: a for a in res.final_schedule.assignments}
    assert by_job["J_DONE"].technician_id == "E1"
    assert by_job["J_DONE"].planned_start_min == 500
    assert by_job["J_PROG"].technician_id == "E1"
    assert by_job["J_PROG"].planned_start_min == 630
    assert by_job["J_CRIT"].technician_id == "E2"


# ---------------------------------------------------------------------------
# Targeted Regression Tests: Protected Assignment Validation (Fix 1)
# ---------------------------------------------------------------------------


def test_valid_locked_future_assignment_remains_at_original_technician_and_start_time() -> None:
    """A valid locked future assignment stays on its technician and start time while preserving travel sequencing."""
    e1 = _make_elec("E1", shift_start=480, shift_end=960)
    e2 = _make_elec("E2", shift_start=480, shift_end=960)
    j_lock = _make_job("J_LOCK", priority="Normal", ws=540, we=780, duration=60, sla=840, status="assigned")
    j_morn = _make_job("J_MORN", priority="High", ws=500, we=560, duration=60, sla=660)

    # E2 is much closer (5m) to J_LOCK than E1 (40m), tempting optimization if J_LOCK were movable.
    # Also J_MORN (500..560) can precede J_LOCK (700) on E1 with J_MORN->J_LOCK travel = 25m.
    locs = ["HOME_E1", "HOME_E2", "J_LOCK", "J_MORN"]
    pair_tt = {
        ("HOME_E1", "J_LOCK"): 40,
        ("HOME_E2", "J_LOCK"): 5,
        ("HOME_E1", "J_MORN"): 15,
        ("HOME_E2", "J_MORN"): 45,
        ("J_MORN", "J_LOCK"): 25,
        ("J_LOCK", "J_MORN"): 25,
    }
    tt = [
        TravelEntry(
            from_location_id=u,
            to_location_id=v,
            travel_time_min=0 if u == v else pair_tt.get((u, v), 20),
        )
        for u in locs
        for v in locs
    ]
    existing = [
        ExistingAssignment(
            job_id="J_LOCK",
            technician_id="E1",
            planned_start_min=700,
            status="assigned",
            locked=True,
        )
    ]

    res = generate_schedule(
        jobs=[j_lock, j_morn],
        electricians=[e1, e2],
        travel_times=tt,
        existing_assignments=existing,
        config=SchedulerConfig(enable_optimization=True),
    )

    assert res.is_valid_for_commitment
    assert res.final_schedule.hard_constraint_violation_count == 0
    by_job = {a.job_id: a for a in res.final_schedule.assignments}
    assert by_job["J_LOCK"].technician_id == "E1"
    assert by_job["J_LOCK"].planned_start_min == 700
    assert by_job["J_LOCK"].is_protected is True
    # Verify predecessor travel sequencing when J_MORN is scheduled ahead of J_LOCK on E1
    assert by_job["J_MORN"].technician_id == "E1"
    assert by_job["J_LOCK"].from_location_id == "J_MORN"
    assert by_job["J_LOCK"].travel_time_min == 25
    assert by_job["J_LOCK"].arrival_min <= by_job["J_LOCK"].planned_start_min


def test_locked_future_assignment_outside_shift_reported_invalid() -> None:
    """Locked future assignments violating shift start or shift end are kept unmoved and reported invalid."""
    e1 = _make_elec("E1", shift_start=480, shift_end=960)
    e2 = _make_elec("E2", shift_start=480, shift_end=960)  # Free alternative tech must NOT receive locked job

    # 1. Late-shift overrun: locked at 930 + 60m duration = 990 > shift_end 960
    j_late_lock = _make_job("J_LATE_LOCK", ws=540, we=950, duration=60, sla=1020, status="assigned")
    locs_late = ["HOME_E1", "HOME_E2", "J_LATE_LOCK"]
    tt_late = [
        TravelEntry(from_location_id=u, to_location_id=v, travel_time_min=0 if u == v else 15)
        for u in locs_late
        for v in locs_late
    ]
    res_late = generate_schedule(
        jobs=[j_late_lock],
        electricians=[e1, e2],
        travel_times=tt_late,
        existing_assignments=[
            ExistingAssignment(
                job_id="J_LATE_LOCK",
                technician_id="E1",
                planned_start_min=930,
                status="assigned",
                locked=True,
            )
        ],
    )
    assert not res_late.is_valid_for_commitment
    assert res_late.final_schedule.hard_constraint_violation_count >= 1
    assert any(ReasonCode.SHIFT_CONSTRAINT.value in err for err in res_late.final_schedule.validation_errors)
    asgn_late = res_late.final_schedule.assignments[0]
    assert asgn_late.technician_id == "E1"
    assert asgn_late.planned_start_min == 930

    # 2. Early-shift violation: start 485 with 15m travel requires departure at 470 < shift_start 480
    j_early_lock = _make_job("J_EARLY_LOCK", ws=480, we=720, duration=60, sla=780, status="assigned")
    locs_early = ["HOME_E1", "HOME_E2", "J_EARLY_LOCK"]
    tt_early = [
        TravelEntry(from_location_id=u, to_location_id=v, travel_time_min=0 if u == v else 15)
        for u in locs_early
        for v in locs_early
    ]
    res_early = generate_schedule(
        jobs=[j_early_lock],
        electricians=[e1, e2],
        travel_times=tt_early,
        existing_assignments=[
            ExistingAssignment(
                job_id="J_EARLY_LOCK",
                technician_id="E1",
                planned_start_min=485,
                status="assigned",
                locked=True,
            )
        ],
    )
    assert not res_early.is_valid_for_commitment
    assert res_early.final_schedule.hard_constraint_violation_count >= 1
    assert any(ReasonCode.SHIFT_CONSTRAINT.value in err for err in res_early.final_schedule.validation_errors)
    asgn_early = res_early.final_schedule.assignments[0]
    assert asgn_early.technician_id == "E1"
    assert asgn_early.planned_start_min == 485


def test_locked_future_assignment_overlapping_unavailability_reported_invalid() -> None:
    """A locked future assignment overlapping technician unavailability is reported invalid without silent movement."""
    e1 = _make_elec("E1", shift_start=480, shift_end=960)
    e2 = _make_elec("E2", shift_start=480, shift_end=960)
    j_lock = _make_job("J_UNAV_LOCK", ws=540, we=840, duration=60, sla=900, status="assigned")
    locs = ["HOME_E1", "HOME_E2", "J_UNAV_LOCK"]
    tt = [
        TravelEntry(from_location_id=u, to_location_id=v, travel_time_min=0 if u == v else 15)
        for u in locs
        for v in locs
    ]
    unavail = [
        UnavailabilityInterval(
            unavailability_id="U_CONFLICT",
            technician_id="E1",
            start_min=600,
            end_min=690,
            reason="Mandatory safety briefing",
        )
    ]

    res = generate_schedule(
        jobs=[j_lock],
        electricians=[e1, e2],
        travel_times=tt,
        unavailability=unavail,
        existing_assignments=[
            ExistingAssignment(
                job_id="J_UNAV_LOCK",
                technician_id="E1",
                planned_start_min=630,
                status="assigned",
                locked=True,
            )
        ],
    )
    assert not res.is_valid_for_commitment
    assert res.final_schedule.hard_constraint_violation_count >= 1
    assert any(
        ReasonCode.NO_AVAILABLE_SLOT.value in err and "U_CONFLICT" in err
        for err in res.final_schedule.validation_errors
    )
    asgn = res.final_schedule.assignments[0]
    assert asgn.technician_id == "E1"
    assert asgn.planned_start_min == 630


def test_locked_future_assignment_violating_window_or_hard_deadline_reported_invalid() -> None:
    """Locked future assignments violating time windows or hard SLA deadlines are reported invalid."""
    e1 = _make_elec("E1", shift_start=480, shift_end=960)
    e2 = _make_elec("E2", shift_start=480, shift_end=960)

    # Case A1: Locked start 510 precedes window_start_min 540
    j_win_early = _make_job("J_WIN_EARLY", ws=540, we=660, duration=60, sla=840, status="assigned")
    locs_we = ["HOME_E1", "HOME_E2", "J_WIN_EARLY"]
    tt_we = [
        TravelEntry(from_location_id=u, to_location_id=v, travel_time_min=0 if u == v else 15)
        for u in locs_we
        for v in locs_we
    ]
    res_win_early = generate_schedule(
        jobs=[j_win_early],
        electricians=[e1, e2],
        travel_times=tt_we,
        existing_assignments=[
            ExistingAssignment(
                job_id="J_WIN_EARLY",
                technician_id="E1",
                planned_start_min=510,
                status="assigned",
                locked=True,
            )
        ],
    )
    assert not res_win_early.is_valid_for_commitment
    assert res_win_early.final_schedule.hard_constraint_violation_count >= 1
    assert any(
        ReasonCode.NO_AVAILABLE_SLOT.value in err
        for err in res_win_early.final_schedule.validation_errors
    )
    assert res_win_early.final_schedule.assignments[0].technician_id == "E1"
    assert res_win_early.final_schedule.assignments[0].planned_start_min == 510

    # Case A2: Locked start 720 exceeds window_end_min 660
    j_win = _make_job("J_WIN_LOCK", ws=540, we=660, duration=60, sla=840, status="assigned")
    locs_w = ["HOME_E1", "HOME_E2", "J_WIN_LOCK"]
    tt_w = [
        TravelEntry(from_location_id=u, to_location_id=v, travel_time_min=0 if u == v else 15)
        for u in locs_w
        for v in locs_w
    ]
    res_win = generate_schedule(
        jobs=[j_win],
        electricians=[e1, e2],
        travel_times=tt_w,
        existing_assignments=[
            ExistingAssignment(
                job_id="J_WIN_LOCK",
                technician_id="E1",
                planned_start_min=720,
                status="assigned",
                locked=True,
            )
        ],
    )
    assert not res_win.is_valid_for_commitment
    assert res_win.final_schedule.hard_constraint_violation_count >= 1
    assert any(ReasonCode.NO_AVAILABLE_SLOT.value in err for err in res_win.final_schedule.validation_errors)
    assert res_win.final_schedule.assignments[0].technician_id == "E1"
    assert res_win.final_schedule.assignments[0].planned_start_min == 720

    # Case B: Locked start 690 + 60m duration = 750 > hard sla_deadline_min 720
    j_sla = _make_job("J_SLA_LOCK", ws=540, we=780, duration=60, sla=720, status="assigned")
    locs_s = ["HOME_E1", "HOME_E2", "J_SLA_LOCK"]
    tt_s = [
        TravelEntry(from_location_id=u, to_location_id=v, travel_time_min=0 if u == v else 15)
        for u in locs_s
        for v in locs_s
    ]
    res_sla = generate_schedule(
        jobs=[j_sla],
        electricians=[e1, e2],
        travel_times=tt_s,
        existing_assignments=[
            ExistingAssignment(
                job_id="J_SLA_LOCK",
                technician_id="E1",
                planned_start_min=690,
                status="assigned",
                locked=True,
            )
        ],
        config=SchedulerConfig(sla_mode="hard"),
    )
    assert not res_sla.is_valid_for_commitment
    assert res_sla.final_schedule.hard_constraint_violation_count >= 1
    assert res_sla.final_schedule.hard_sla_violation_count >= 1
    assert any(
        ReasonCode.SLA_DEADLINE_INFEASIBLE.value in err
        for err in res_sla.final_schedule.validation_errors
    )
    assert res_sla.final_schedule.assignments[0].technician_id == "E1"
    assert res_sla.final_schedule.assignments[0].planned_start_min == 690


def test_completed_and_in_progress_commitments_remain_protected_during_optimization_and_recovery() -> None:
    """Completed and active work retain exact historical/active timing fields and are undisturbed by recovery/optimization."""
    e1 = _make_elec("E1", shift_start=480, shift_end=960)
    e2 = _make_elec("E2", shift_start=480, shift_end=960)

    # Historical completed job with explicit non-tight wait gap (arrived 500, started 510, completed 565)
    j_done = _make_job("J_DONE", ws=500, we=600, duration=60, sla=660, status="completed")
    # Active in-progress job with explicit departure/arrival (departed 575, arrived 590, started 600)
    j_act = _make_job("J_ACT", ws=590, we=660, duration=60, sla=720, status="in_progress")
    # Early pending job that would fit [480, 505] only if illegally inserted BEFORE completed J_DONE
    j_early_new = _make_job("J_EARLY_NEW", priority="Critical", ws=485, we=500, duration=20, sla=600)
    # Afternoon pending job scheduled during recovery
    j_aft = _make_job("J_AFT", priority="High", ws=720, we=840, duration=60, sla=900)

    locs = ["HOME_E1", "HOME_E2", "J_DONE", "J_ACT", "J_EARLY_NEW", "J_AFT"]
    tt = [
        TravelEntry(from_location_id=u, to_location_id=v, travel_time_min=0 if u == v else 15)
        for u in locs
        for v in locs
    ]
    # Mid-day unavailability starting at 630 overlaps tail of already in-progress J_ACT [600, 660)
    unavail = [
        UnavailabilityInterval(
            unavailability_id="U_EMERG",
            technician_id="E1",
            start_min=630,
            end_min=700,
            reason="Mid-day emergency",
        )
    ]
    existing = [
        ExistingAssignment(
            job_id="J_DONE",
            technician_id="E1",
            departure_min=485,
            arrival_min=500,
            planned_start_min=510,
            completion_min=565,
            status="completed",
            locked=True,
        ),
        ExistingAssignment(
            job_id="J_ACT",
            technician_id="E1",
            departure_min=575,
            arrival_min=590,
            planned_start_min=600,
            completion_min=660,
            status="in_progress",
            locked=True,
        ),
    ]

    res = generate_schedule(
        jobs=[j_done, j_act, j_early_new, j_aft],
        electricians=[e1, e2],
        travel_times=tt,
        unavailability=unavail,
        existing_assignments=existing,
        config=SchedulerConfig(enable_optimization=True),
    )

    assert res.is_valid_for_commitment
    assert res.final_schedule.hard_constraint_violation_count == 0
    by_job = {a.job_id: a for a in res.final_schedule.assignments}

    # Historical & active timing fields must remain completely un-recalculated
    assert by_job["J_DONE"].technician_id == "E1"
    assert by_job["J_DONE"].route_position == 0
    assert (
        by_job["J_DONE"].departure_min,
        by_job["J_DONE"].arrival_min,
        by_job["J_DONE"].planned_start_min,
        by_job["J_DONE"].completion_min,
    ) == (485, 500, 510, 565)

    assert by_job["J_ACT"].technician_id == "E1"
    assert by_job["J_ACT"].route_position == 1
    assert (
        by_job["J_ACT"].departure_min,
        by_job["J_ACT"].arrival_min,
        by_job["J_ACT"].planned_start_min,
        by_job["J_ACT"].completion_min,
    ) == (575, 590, 600, 660)

    # J_EARLY_NEW was not inserted before completed work on E1; it went cleanly to E2
    assert by_job["J_EARLY_NEW"].technician_id == "E2"

    # Independently verify validate_full_schedule flags tampering if historical departure_min is altered
    cfg = SchedulerConfig()
    rj_done, _ = validate_job_data(j_done, cfg)
    assert rj_done is not None
    tampered_stop = RouteStop(
        job=rj_done,
        technician_id="E1",
        from_location_id="HOME_E1",
        departure_min=495,  # Altered from historical 485!
        arrival_min=510,
        planned_start_min=510,
        completion_min=565,
        travel_time_min=15,
        status="completed",
        is_protected=True,
        locked_completion_min=565,
    )
    tampered_check = validate_full_schedule(
        routes_by_tech={"E1": [tampered_stop]},
        electricians_by_id={"E1": e1},
        valid_jobs_by_id={"J_DONE": rj_done},
        unavailability_by_tech={},
        existing_assignments=[existing[0]],
        travel_matrix=TravelMatrix(entries=tt),
        config=cfg,
    )
    assert not tampered_check.is_valid
    assert tampered_check.protected_violation_count >= 1


def test_valid_schedule_with_protected_commitments_passes_validation() -> None:
    """A valid schedule combining completed, in-progress, valid locked future, and unlocked jobs passes validation."""
    cfg = SchedulerConfig(enable_optimization=True)
    e1 = _make_elec("E1", shift_start=480, shift_end=960)
    e2 = _make_elec("E2", shift_start=480, shift_end=960)

    j_done = _make_job("J_DONE", ws=495, we=540, duration=60, sla=600, status="completed")
    j_prog = _make_job("J_PROG", ws=570, we=630, duration=60, sla=690, status="in_progress")
    j_lock = _make_job("J_LOCK_FUT", ws=720, we=800, duration=60, sla=880, status="assigned")
    j_free1 = _make_job("J_FREE_1", priority="High", ws=540, we=660, duration=60, sla=720)
    j_free2 = _make_job("J_FREE_2", priority="Normal", ws=800, we=880, duration=45, sla=950)

    locs = ["HOME_E1", "HOME_E2", "J_DONE", "J_PROG", "J_LOCK_FUT", "J_FREE_1", "J_FREE_2"]
    tt = [
        TravelEntry(from_location_id=u, to_location_id=v, travel_time_min=0 if u == v else 15)
        for u in locs
        for v in locs
    ]
    existing = [
        ExistingAssignment(
            job_id="J_DONE",
            technician_id="E1",
            departure_min=480,
            arrival_min=495,
            planned_start_min=495,
            completion_min=555,
            status="completed",
            locked=True,
        ),
        ExistingAssignment(
            job_id="J_PROG",
            technician_id="E1",
            departure_min=555,
            arrival_min=570,
            planned_start_min=570,
            completion_min=630,
            status="in_progress",
            locked=True,
        ),
        ExistingAssignment(
            job_id="J_LOCK_FUT",
            technician_id="E2",
            planned_start_min=750,
            status="assigned",
            locked=True,
        ),
    ]

    res = generate_schedule(
        jobs=[j_done, j_prog, j_lock, j_free1, j_free2],
        electricians=[e1, e2],
        travel_times=tt,
        existing_assignments=existing,
        config=cfg,
    )

    assert res.is_valid_for_commitment
    assert res.final_schedule.is_valid_for_commitment
    assert res.final_schedule.hard_constraint_violation_count == 0
    assert res.final_schedule.hard_sla_violation_count == 0
    assert res.final_schedule.objective.protected_violation_count == 0
    assert res.final_schedule.validation_errors == []
    assert set(res.assigned_job_ids) == {"J_DONE", "J_PROG", "J_LOCK_FUT", "J_FREE_1", "J_FREE_2"}

    by_job = {a.job_id: a for a in res.final_schedule.assignments}
    assert (by_job["J_DONE"].technician_id, by_job["J_DONE"].planned_start_min) == ("E1", 495)
    assert (by_job["J_PROG"].technician_id, by_job["J_PROG"].planned_start_min) == ("E1", 570)
    assert (by_job["J_LOCK_FUT"].technician_id, by_job["J_LOCK_FUT"].planned_start_min) == ("E2", 750)


