"""Regression tests for 5-minute technician assignment timeout, accept/reject, retry, and concurrency guards."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from app.scheduler.dataset_loader import load_dataset_bundle
from app.scheduler.dispatch import (
    DispatchConflictError,
    DispatchSession,
    OfferNotFoundError,
    StaleOfferError,
)
from app.scheduler.engine import generate_schedule
from app.schemas.dispatch_recovery import (
     DEFAULT_ASSIGNMENT_TIMEOUT_SECONDS,
    DispatchConfig,
    JobDispatchStatus,
    OfferStatus,
)
from app.schemas.scheduling import (
    Electrician,
    ExistingAssignment,
    Job,
    SchedulerConfig,
    TravelEntry,
)


BASE_NOW = datetime(2026, 5, 4, 8, 0, 0, tzinfo=timezone.utc)


def _three_tech_fixture() -> tuple[list[Electrician], list[Job], list[TravelEntry]]:
    elecs = [
        Electrician(
            technician_id="E001",
            name="Tech 1 (Closest)",
            skills=["fault_diagnosis"],
            eligible_zones=["Central"],
            shift_start_min=480,
            shift_end_min=1020,
        ),
        Electrician(
            technician_id="E002",
            name="Tech 2 (Second)",
            skills=["fault_diagnosis"],
            eligible_zones=["Central"],
            shift_start_min=480,
            shift_end_min=1020,
        ),
        Electrician(
            technician_id="E003",
            name="Tech 3 (Ineligible Skill)",
            skills=["lighting_systems"],
            eligible_zones=["Central"],
            shift_start_min=480,
            shift_end_min=1020,
        ),
    ]
    jobs = [
        Job(
            job_id="J001",
            required_skills=["fault_diagnosis"],
            priority="High",
            duration_min=60,
            zone="Central",
            window_start_min=540,
            window_end_min=720,
            sla_deadline_min=840,
        )
    ]
    travel = [
        TravelEntry(from_location_id="HOME_E001", to_location_id="J001", travel_time_min=10),
        TravelEntry(from_location_id="HOME_E002", to_location_id="J001", travel_time_min=25),
        TravelEntry(from_location_id="HOME_E003", to_location_id="J001", travel_time_min=5),
    ]
    return elecs, jobs, travel


def test_five_minute_timeout_boundary_accept_at_299s_vs_expire_at_300s() -> None:
    assert DEFAULT_ASSIGNMENT_TIMEOUT_SECONDS == 300

    elecs, jobs, travel = _three_tech_fixture()
    sched = generate_schedule(jobs=jobs, electricians=elecs, travel_times=travel)

    # Case A: Accept at +299s (within 5-minute window) succeeds and locks assignment
    session_ok = DispatchSession(
        schedule_result=sched,
        jobs=jobs,
        electricians=elecs,
        travel_times=travel,
        now_utc=BASE_NOW,
        auto_offer_all=True,
    )
    snap0 = session_ok.snapshot()
    first_offer = snap0.job_states["J001"].offers[0]
    assert first_offer.technician_id == "E001"
    assert first_offer.expires_at_utc == BASE_NOW + timedelta(seconds=300)

    accept_res = session_ok.respond_to_offer(
        offer_id=first_offer.offer_id,
        technician_id="E001",
        decision="accept",
        responded_at_utc=BASE_NOW + timedelta(seconds=299),
    )
    assert accept_res.action == "offer_accepted"
    assert accept_res.state.is_valid_for_commitment is True
    j_state = accept_res.state.job_states["J001"]
    assert j_state.dispatch_status == JobDispatchStatus.ACCEPTED
    assert j_state.assigned_technician_id == "E001"
    committed_asgn = accept_res.state.current_schedule.assignments[0]
    assert committed_asgn.technician_id == "E001"
    assert committed_asgn.is_protected is True

    # Case B: Late accept at exact +300s boundary raises StaleOfferError and retries E002
    session_late = DispatchSession(
        schedule_result=sched,
        jobs=jobs,
        electricians=elecs,
        travel_times=travel,
        now_utc=BASE_NOW,
        auto_offer_all=True,
    )
    off1 = session_late.snapshot().job_states["J001"].offers[0]
    with pytest.raises(StaleOfferError) as exc_info:
        session_late.respond_to_offer(
            offer_id=off1.offer_id,
            technician_id="E001",
            decision="accept",
            responded_at_utc=BASE_NOW + timedelta(seconds=300),
        )
    assert exc_info.value.error_code == "STALE_OFFER_EXPIRED"

    snap_after = session_late.snapshot()
    j_late = snap_after.job_states["J001"]
    assert j_late.offers[0].status == OfferStatus.TIMED_OUT
    assert j_late.dispatch_status == JobDispatchStatus.PENDING_RESPONSE
    assert j_late.assigned_technician_id == "E002"
    assert len(j_late.offers) == 2
    assert j_late.offers[1].technician_id == "E002"
    assert j_late.offers[1].attempt_number == 2
    assert snap_after.is_valid_for_commitment is True


def test_rejection_triggers_next_eligible_technician_and_records_explanations() -> None:
    elecs, jobs, travel = _three_tech_fixture()
    sched = generate_schedule(jobs=jobs, electricians=elecs, travel_times=travel)
    session = DispatchSession(
        schedule_result=sched,
        jobs=jobs,
        electricians=elecs,
        travel_times=travel,
        now_utc=BASE_NOW,
        auto_offer_all=True,
    )

    off1 = session.snapshot().job_states["J001"].offers[0]
    assert off1.technician_id == "E001"

    rej_res = session.respond_to_offer(
        offer_id=off1.offer_id,
        technician_id="E001",
        decision="reject",
        reason="Missing specialized meter in van",
        responded_at_utc=BASE_NOW + timedelta(seconds=45),
    )
    assert rej_res.action == "offer_rejected"
    assert len(rej_res.new_offers) == 1
    off2 = rej_res.new_offers[0]
    assert off2.technician_id == "E002"
    assert off2.attempt_number == 2
    assert off2.selection_explanation is not None
    # Rejected alternatives include E001's rejection and E003's skill ineligibility
    rej_techs = {r.technician_id for r in off2.rejected_alternatives}
    assert "E001" in rej_techs

    # E002 accepts offer #2
    acc_res = session.respond_to_offer(
        offer_id=off2.offer_id,
        technician_id="E002",
        decision="accept",
        responded_at_utc=BASE_NOW + timedelta(seconds=90),
    )
    assert acc_res.state.job_states["J001"].dispatch_status == JobDispatchStatus.ACCEPTED
    assert acc_res.state.job_states["J001"].assigned_technician_id == "E002"
    assert acc_res.state.is_valid_for_commitment is True
    assert [a.job_id for a in acc_res.state.current_schedule.assignments] == ["J001"]
    assert acc_res.state.current_schedule.assignments[0].technician_id == "E002"


def test_stale_superseded_wrong_tech_and_duplicate_offers_blocked() -> None:
    elecs, jobs, travel = _three_tech_fixture()
    sched = generate_schedule(jobs=jobs, electricians=elecs, travel_times=travel)
    session = DispatchSession(
        schedule_result=sched,
        jobs=jobs,
        electricians=elecs,
        travel_times=travel,
        now_utc=BASE_NOW,
        auto_offer_all=True,
    )

    off1 = session.snapshot().job_states["J001"].offers[0]

    # Duplicate manual offer while off1 is still pending -> DispatchConflictError
    with pytest.raises(DispatchConflictError) as dup_pending:
        session.offer_job("J001", now_utc=BASE_NOW + timedelta(seconds=10))
    assert dup_pending.value.error_code == "CONCURRENT_DISPATCH_CONFLICT"

    # Wrong technician attempting to accept off1 -> DispatchConflictError
    with pytest.raises(DispatchConflictError) as wrong_tech:
        session.respond_to_offer(
            offer_id=off1.offer_id,
            technician_id="E002",
            decision="accept",
            responded_at_utc=BASE_NOW + timedelta(seconds=20),
        )
    assert wrong_tech.value.error_code == "TECHNICIAN_MISMATCH"

    # Unknown offer_id -> OfferNotFoundError
    with pytest.raises(OfferNotFoundError):
        session.respond_to_offer(
            offer_id="off-nonexistent",
            technician_id="E001",
            decision="accept",
            responded_at_utc=BASE_NOW + timedelta(seconds=20),
        )

    # E001 rejects -> advances to off2 on E002
    rej = session.respond_to_offer(
        offer_id=off1.offer_id,
        technician_id="E001",
        decision="reject",
        responded_at_utc=BASE_NOW + timedelta(seconds=30),
    )
    off2 = rej.new_offers[0]

    # Stale response from E001 on superseded off1 -> StaleOfferError; off2 remains intact
    with pytest.raises(StaleOfferError) as stale_sup:
        session.respond_to_offer(
            offer_id=off1.offer_id,
            technician_id="E001",
            decision="accept",
            responded_at_utc=BASE_NOW + timedelta(seconds=40),
        )
    assert stale_sup.value.error_code == "STALE_OFFER_SUPERSEDED"
    assert session.snapshot().job_states["J001"].active_offer_id == off2.offer_id

    # E002 accepts off2 -> duplicate accept & duplicate offer_job are both blocked
    session.respond_to_offer(
        offer_id=off2.offer_id,
        technician_id="E002",
        decision="accept",
        responded_at_utc=BASE_NOW + timedelta(seconds=50),
    )
    with pytest.raises(DispatchConflictError) as dup_acc:
        session.respond_to_offer(
            offer_id=off2.offer_id,
            technician_id="E002",
            decision="accept",
            responded_at_utc=BASE_NOW + timedelta(seconds=55),
        )
    assert dup_acc.value.error_code == "OFFER_ALREADY_FINALIZED"

    with pytest.raises(DispatchConflictError) as already_asgn:
        session.offer_job("J001", now_utc=BASE_NOW + timedelta(seconds=60))
    assert already_asgn.value.error_code == "JOB_ALREADY_ASSIGNED"


def test_no_eligible_technician_remains_transitions_to_exhausted_unassigned() -> None:
    elecs, jobs, travel = _three_tech_fixture()
    sched = generate_schedule(jobs=jobs, electricians=elecs, travel_times=travel)
    session = DispatchSession(
        schedule_result=sched,
        jobs=jobs,
        electricians=elecs,
        travel_times=travel,
        now_utc=BASE_NOW,
        auto_offer_all=True,
    )

    # Attempt #1 (E001) rejects at +60s -> retries E002 (attempt #2, expires at +360s)
    off1 = session.snapshot().job_states["J001"].offers[0]
    rej = session.respond_to_offer(
        offer_id=off1.offer_id,
        technician_id="E001",
        decision="reject",
        reason="Out of parts",
        responded_at_utc=BASE_NOW + timedelta(seconds=60),
    )
    off2 = rej.new_offers[0]
    assert off2.technician_id == "E002"
    assert off2.expires_at_utc == BASE_NOW + timedelta(seconds=360)

    # Sweep before off2's 5-min deadline (+359s) -> nothing expires yet
    early_sweep = session.sweep_timeouts(now_utc=BASE_NOW + timedelta(seconds=359))
    assert early_sweep.timed_out_offer_ids == []

    # Sweep at +360s -> E002 times out; E003 lacks fault_diagnosis -> EXHAUSTED_UNASSIGNED!
    sweep_res = session.sweep_timeouts(now_utc=BASE_NOW + timedelta(seconds=360))
    assert sweep_res.timed_out_offer_ids == [off2.offer_id]
    assert sweep_res.new_offers == []
    assert sweep_res.exhausted_job_ids == ["J001"]

    final_state = sweep_res.state
    j_rec = final_state.job_states["J001"]
    assert j_rec.dispatch_status == JobDispatchStatus.EXHAUSTED_UNASSIGNED
    assert j_rec.assigned_technician_id is None
    assert j_rec.active_offer_id is None
    assert j_rec.final_unassigned_reason is not None
    assert "E001" in j_rec.final_unassigned_reason.summary
    assert "E002" in j_rec.final_unassigned_reason.summary
    assert final_state.current_schedule.assigned_job_ids == []
    assert final_state.current_schedule.unassigned_job_ids == ["J001"]
    assert final_state.is_valid_for_commitment is True


def test_concurrent_multithreaded_offers_and_responses_prevent_double_booking() -> None:
    """Two jobs compete for a tight shift on E002 after E001 rejects, under concurrent threads."""
    elecs = [
        Electrician(
            technician_id="E001",
            name="Tech 1",
            skills=["fault_diagnosis"],
            eligible_zones=["Central"],
            shift_start_min=480,
            shift_end_min=600,  # Only fits ONE 90m job
        ),
        Electrician(
            technician_id="E002",
            name="Tech 2",
            skills=["fault_diagnosis"],
            eligible_zones=["Central"],
            shift_start_min=480,
            shift_end_min=600,  # Only fits ONE 90m job
        ),
        Electrician(
            technician_id="E003",
            name="Tech 3",
            skills=["fault_diagnosis"],
            eligible_zones=["Central"],
            shift_start_min=480,
            shift_end_min=600,  # Backup slot so retry has at most 1 per tech
        ),
    ]
    jobs = [
        Job(
            job_id="J_A",
            required_skills=["fault_diagnosis"],
            priority="Critical",
            duration_min=90,
            zone="Central",
            window_start_min=490,
            window_end_min=510,
            sla_deadline_min=600,
        ),
        Job(
            job_id="J_B",
            required_skills=["fault_diagnosis"],
            priority="High",
            duration_min=90,
            zone="Central",
            window_start_min=490,
            window_end_min=510,
            sla_deadline_min=600,
        ),
    ]
    travel = [
        TravelEntry(from_location_id=f"HOME_{tid}", to_location_id=jid, travel_time_min=10)
        for tid in ("E001", "E002", "E003")
        for jid in ("J_A", "J_B")
    ] + [
        TravelEntry(from_location_id="J_A", to_location_id="J_B", travel_time_min=10),
        TravelEntry(from_location_id="J_B", to_location_id="J_A", travel_time_min=10),
    ]

    sched = generate_schedule(jobs=jobs, electricians=elecs, travel_times=travel)
    session = DispatchSession(
        schedule_result=sched,
        jobs=jobs,
        electricians=elecs,
        travel_times=travel,
        now_utc=BASE_NOW,
        auto_offer_all=True,
    )
    init_snap = session.snapshot()
    off_a = init_snap.job_states["J_A"].offers[0]
    off_b = init_snap.job_states["J_B"].offers[0]

    # Race 12 threads simultaneously trying to accept/reject off_a, reject off_b, and re-offer J_A/J_B
    def _worker(idx: int):
        ts = BASE_NOW + timedelta(seconds=10 + idx)
        if idx % 3 == 0:
            return session.respond_to_offer(off_a.offer_id, off_a.technician_id, "reject", responded_at_utc=ts)
        if idx % 3 == 1:
            return session.respond_to_offer(off_b.offer_id, off_b.technician_id, "reject", responded_at_utc=ts)
        return session.offer_job("J_A", now_utc=ts)

    outcomes = []
    errors = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_worker, i) for i in range(12)]
        for fut in futures:
            try:
                outcomes.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

    # Exactly 2 rejections can succeed (one for off_a, one for off_b); all other 10 calls must be safely blocked!
    assert len(outcomes) == 2
    assert len(errors) == 10

    snap = session.snapshot()
    assert snap.is_valid_for_commitment is True
    # Verify no duplicate job assignments and at most 1 job per technician (90m jobs cannot share a 120m shift)
    techs_used = [a.technician_id for a in snap.current_schedule.assignments]
    assert len(techs_used) == len(set(techs_used))
    job_ids_assigned = [a.job_id for a in snap.current_schedule.assignments]
    assert len(job_ids_assigned) == len(set(job_ids_assigned))


def test_bundled_dataset_timeout_sweep_preserves_locked_commitments_and_schedule_validity() -> None:
    bundle = load_dataset_bundle()
    existing = [
        ExistingAssignment(
            job_id="J034",
            technician_id="E004",
            departure_min=480,
            arrival_min=495,
            planned_start_min=495,
            completion_min=585,
            status="completed",
            locked=True,
        )
    ]
    sched = generate_schedule(
        jobs=bundle.jobs,
        electricians=bundle.electricians,
        travel_times=bundle.travel_entries,
        unavailability=bundle.unavailability,
        existing_assignments=existing,
        config=SchedulerConfig(enable_optimization=False),
    )
    session = DispatchSession(
        schedule_result=sched,
        jobs=bundle.jobs,
        electricians=bundle.electricians,
        travel_times=bundle.travel_entries,
        unavailability=bundle.unavailability,
        existing_assignments=existing,
        dispatch_config=DispatchConfig(response_timeout_seconds=300),
        now_utc=BASE_NOW,
        auto_offer_all=True,
    )

    init_snap = session.snapshot()
    assert init_snap.locked_committed_count == 1
    assert init_snap.job_states["J034"].dispatch_status == JobDispatchStatus.LOCKED_COMMITTED
    assert init_snap.pending_offer_count == len(sched.assigned_job_ids) - 1

    # Sweep all pending offers after 5 minutes -> retries where eligible, never touches J034, stays valid!
    swept = session.sweep_timeouts(now_utc=BASE_NOW + timedelta(seconds=300))
    assert len(swept.timed_out_offer_ids) == init_snap.pending_offer_count
    assert swept.state.is_valid_for_commitment is True
    assert swept.state.current_schedule.hard_constraint_violation_count == 0
    j034_asgn = next(a for a in swept.state.current_schedule.assignments if a.job_id == "J034")
    assert j034_asgn.technician_id == "E004"
    assert j034_asgn.planned_start_min == 495
    assert j034_asgn.status == "completed"

