"""Tests for schedule generation, versioning, human approval workflow, recovery protection, candidate ranking, metrics, and seed repeatability."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.seed_data import seed_database
from tests.test_jobs import _sample_job_payload, _sample_tech_payload


def test_schedule_persistence_human_approval_and_comparison(client: TestClient) -> None:
    # Create 2 technicians and 2 jobs in BLR-CENTRAL-MG-ROAD
    t1 = client.post(
        "/api/v1/technicians",
        json=_sample_tech_payload(name="Tech One", latitude=12.9716, longitude=77.5946),
    ).json()
    t2 = client.post(
        "/api/v1/technicians",
        json=_sample_tech_payload(name="Tech Two", latitude=12.9750, longitude=77.5980),
    ).json()

    j1 = client.post(
        "/api/v1/jobs",
        json=_sample_job_payload(
            customer_name="Job Alpha",
            appointment_window_start="2026-10-30T09:00:00+05:30",
            appointment_window_end="2026-10-30T11:30:00+05:30",
        ),
    ).json()
    j2 = client.post(
        "/api/v1/jobs",
        json=_sample_job_payload(
            customer_name="Job Beta",
            appointment_window_start="2026-10-30T11:00:00+05:30",
            appointment_window_end="2026-10-30T14:00:00+05:30",
        ),
    ).json()

    # 1. Generate initial schedule with auto_activate=True (allowed when no active schedule exists)
    gen_resp = client.post(
        "/api/v1/schedules/generate",
        json={
            "idempotency_key": "init-run-001",
            "run_type": "INITIAL",
            "strategy": "BALANCED",
            "horizon_start": "2026-10-30T08:00:00+05:30",
            "horizon_end": "2026-10-30T18:00:00+05:30",
            "auto_activate": True,
        },
    )
    assert gen_resp.status_code == 201
    v1_data = gen_resp.json()
    v1_id = v1_data["schedule_version"]["id"]
    assert v1_data["schedule_version"]["status"] == "ACTIVE"
    assert v1_data["assigned_job_count"] == 2

    # 2. Duplicate idempotency key must return 409 DUPLICATE_IDEMPOTENCY_KEY
    dup_resp = client.post(
        "/api/v1/schedules/generate",
        json={
            "idempotency_key": "init-run-001",
            "run_type": "INITIAL",
            "strategy": "BALANCED",
            "horizon_start": "2026-10-30T08:00:00+05:30",
            "horizon_end": "2026-10-30T18:00:00+05:30",
        },
    )
    assert dup_resp.status_code == 409
    assert dup_resp.json()["error"]["code"] == "DUPLICATE_IDEMPOTENCY_KEY"

    # 3. Recovery run with auto_activate=True must be rejected (Mandatory Addition #4)
    auto_rec_resp = client.post(
        "/api/v1/schedules/generate",
        json={
            "idempotency_key": "rec-illegal-auto",
            "run_type": "RECOVERY",
            "strategy": "STABILITY_FIRST",
            "horizon_start": "2026-10-30T08:00:00+05:30",
            "horizon_end": "2026-10-30T18:00:00+05:30",
            "auto_activate": True,
        },
    )
    assert auto_rec_resp.status_code == 400
    assert auto_rec_resp.json()["error"]["code"] == "APPROVAL_REQUIRED"

    # 4. Generate a valid RECOVERY proposal (DRAFT) reassigning j2 to t2
    v1_j1_assign = next(a for a in v1_data["assignments"] if a["job_id"] == j1["id"])
    rec_resp = client.post(
        "/api/v1/schedules/generate",
        json={
            "idempotency_key": "rec-draft-002",
            "run_type": "RECOVERY",
            "strategy": "STABILITY_FIRST",
            "horizon_start": "2026-10-30T08:00:00+05:30",
            "horizon_end": "2026-10-30T18:00:00+05:30",
            "auto_activate": False,
            "proposed_assignments": [
                {
                    "job_id": j1["id"],
                    "technician_id": v1_j1_assign["technician_id"],
                    "planned_start_time": v1_j1_assign["planned_start_time"],
                    "planned_end_time": v1_j1_assign["planned_end_time"],
                    "estimated_travel_minutes": v1_j1_assign["estimated_travel_minutes"],
                },
                {
                    "job_id": j2["id"],
                    "technician_id": t2["id"],
                    "planned_start_time": "2026-10-30T11:30:00+05:30",
                    "planned_end_time": "2026-10-30T12:30:00+05:30",
                    "estimated_travel_minutes": 10,
                },
            ],
        },
    )
    assert rec_resp.status_code == 201
    v2_data = rec_resp.json()
    v2_id = v2_data["schedule_version"]["id"]
    assert v2_data["schedule_version"]["status"] == "DRAFT"

    # Current active schedule must STILL be v1 before human approval
    curr_resp = client.get("/api/v1/schedules/current")
    assert curr_resp.status_code == 200
    assert curr_resp.json()["schedule_version"]["id"] == v1_id

    # 5. Compare v1 and v2 metrics and assignment changes
    cmp_resp = client.get(f"/api/v1/schedules/{v1_id}/compare/{v2_id}")
    assert cmp_resp.status_code == 200
    cmp_body = cmp_resp.json()
    assert cmp_body["base_version_number"] == 1
    assert cmp_body["target_version_number"] == 2
    assert "deltas" in cmp_body

    # 6. Operations Manager approves v2 -> v2 becomes ACTIVE, v1 becomes SUPERSEDED
    app_resp = client.post(
        f"/api/v1/schedules/{v2_id}/approve",
        json={
            "approved_by": "ops_manager_anita",
            "reason": "Approved recovery proposal",
        },
    )
    assert app_resp.status_code == 200
    assert app_resp.json()["schedule_version"]["status"] == "ACTIVE"

    v1_after = client.get(f"/api/v1/schedules/{v1_id}").json()
    assert v1_after["schedule_version"]["status"] == "SUPERSEDED"


def test_transaction_rollback_and_recovery_protection_on_failed_schedule(
    client: TestClient,
) -> None:
    t1 = client.post("/api/v1/technicians", json=_sample_tech_payload(name="Tech A")).json()
    t2 = client.post("/api/v1/technicians", json=_sample_tech_payload(name="Tech B")).json()
    j1 = client.post("/api/v1/jobs", json=_sample_job_payload(customer_name="Active Job")).json()

    # Create active schedule v1
    v1 = client.post(
        "/api/v1/schedules/generate",
        json={
            "idempotency_key": "v1-active",
            "run_type": "INITIAL",
            "strategy": "BALANCED",
            "horizon_start": "2026-10-30T08:00:00+05:30",
            "horizon_end": "2026-10-30T18:00:00+05:30",
            "auto_activate": True,
            "proposed_assignments": [
                {
                    "job_id": j1["id"],
                    "technician_id": t1["id"],
                    "planned_start_time": "2026-10-30T09:00:00+05:30",
                    "planned_end_time": "2026-10-30T10:00:00+05:30",
                    "estimated_travel_minutes": 10,
                }
            ],
        },
    ).json()
    v1_id = v1["schedule_version"]["id"]

    # Transition j1 to IN_PROGRESS
    client.patch(
        f"/api/v1/jobs/{j1['id']}/status",
        json={
            "status": "IN_PROGRESS",
            "actual_start_time": "2026-10-30T09:00:00+05:30",
        },
    )

    # Attempt a recovery run that reassigns IN_PROGRESS j1 to t2 -> Must fail & rollback
    bad_rec = client.post(
        "/api/v1/schedules/generate",
        json={
            "idempotency_key": "bad-recovery-attempt",
            "run_type": "RECOVERY",
            "strategy": "STABILITY_FIRST",
            "horizon_start": "2026-10-30T08:00:00+05:30",
            "horizon_end": "2026-10-30T18:00:00+05:30",
            "auto_activate": False,
            "proposed_assignments": [
                {
                    "job_id": j1["id"],
                    "technician_id": t2["id"],
                    "planned_start_time": "2026-10-30T10:00:00+05:30",
                    "planned_end_time": "2026-10-30T11:00:00+05:30",
                    "estimated_travel_minutes": 10,
                }
            ],
        },
    )
    assert bad_rec.status_code == 409
    assert bad_rec.json()["error"]["code"] == "IMMUTABLE_JOB_VIOLATION"

    # Verify active schedule v1 is completely untouched and no v2 was persisted
    versions = client.get("/api/v1/schedules/versions").json()
    assert len(versions) == 1
    assert versions[0]["id"] == v1_id


def test_overlapping_assignments_rejected(client: TestClient) -> None:
    t1 = client.post("/api/v1/technicians", json=_sample_tech_payload()).json()
    j1 = client.post("/api/v1/jobs", json=_sample_job_payload(customer_name="J1")).json()
    j2 = client.post("/api/v1/jobs", json=_sample_job_payload(customer_name="J2")).json()

    overlap_resp = client.post(
        "/api/v1/schedules/generate",
        json={
            "idempotency_key": "overlap-run",
            "run_type": "INITIAL",
            "strategy": "BALANCED",
            "horizon_start": "2026-10-30T08:00:00+05:30",
            "horizon_end": "2026-10-30T18:00:00+05:30",
            "proposed_assignments": [
                {
                    "job_id": j1["id"],
                    "technician_id": t1["id"],
                    "planned_start_time": "2026-10-30T09:00:00+05:30",
                    "planned_end_time": "2026-10-30T10:30:00+05:30",
                    "estimated_travel_minutes": 10,
                },
                {
                    "job_id": j2["id"],
                    "technician_id": t1["id"],
                    "planned_start_time": "2026-10-30T10:00:00+05:30",
                    "planned_end_time": "2026-10-30T11:00:00+05:30",
                    "estimated_travel_minutes": 10,
                },
            ],
        },
    )
    assert overlap_resp.status_code == 409
    assert overlap_resp.json()["error"]["code"] == "ASSIGNMENT_OVERLAP"


def test_candidate_ranking_excludes_infeasible_and_documents_weights(
    client: TestClient,
) -> None:
    feasible_tech = client.post(
        "/api/v1/technicians",
        json=_sample_tech_payload(name="Feasible Tech"),
    ).json()
    infeasible_tech = client.post(
        "/api/v1/technicians",
        json=_sample_tech_payload(
            name="Wrong Zone Tech",
            service_zones=["BLR-NORTH-HEBBAL"],
        ),
    ).json()
    job = client.post("/api/v1/jobs", json=_sample_job_payload()).json()

    rank_resp = client.post(
        "/api/v1/schedules/rank-candidates",
        json={"job_id": job["id"]},
    )
    assert rank_resp.status_code == 200
    body = rank_resp.json()
    assert body["is_globally_optimal"] is False
    assert "travel_time" in body["scoring_weights"]
    assert len(body["feasible_candidates"]) == 1
    assert body["feasible_candidates"][0]["technician_id"] == feasible_tech["id"]
    assert len(body["infeasible_candidates"]) == 1
    assert body["infeasible_candidates"][0]["technician_id"] == infeasible_tech["id"]


def test_seed_data_repeatability_and_counts(db_session: Session) -> None:
    first_run = seed_database(db_session, reset=True)
    assert first_run["total_technicians"] == 20
    assert first_run["total_jobs"] == 100
    assert first_run["technicians_created"] == 20
    assert first_run["jobs_created"] == 100

    # Rerun without reset -> idempotent (0 new duplicates created)
    second_run = seed_database(db_session, reset=False)
    assert second_run["total_technicians"] == 20
    assert second_run["total_jobs"] == 100
    assert second_run["technicians_created"] == 0
    assert second_run["jobs_created"] == 0


def test_full_seeded_dataset_optimization_and_metrics(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_database(db_session, reset=True)

    # Verify initial seeded ACTIVE schedule v1 exists with 8 locked jobs (4 COMPLETED + 4 IN_PROGRESS)
    curr = client.get("/api/v1/schedules/current")
    assert curr.status_code == 200
    v1_id = curr.json()["schedule_version"]["id"]
    assert curr.json()["assigned_job_count"] == 8

    # Generate an OPTIMIZATION schedule proposal (v2 DRAFT) across all 100 jobs
    opt_resp = client.post(
        "/api/v1/schedules/generate",
        json={
            "idempotency_key": "full-dataset-opt-v2",
            "run_type": "OPTIMIZATION",
            "strategy": "BALANCED",
            "horizon_start": "2026-10-30T06:00:00+05:30",
            "horizon_end": "2026-10-30T23:59:00+05:30",
            "auto_activate": False,
        },
    )
    assert opt_resp.status_code == 201
    v2 = opt_resp.json()
    v2_id = v2["schedule_version"]["id"]
    assert v2["schedule_version"]["status"] == "DRAFT"
    # Must assign a large majority of jobs while leaving the 8 deliberately infeasible jobs unassigned
    assert v2["assigned_job_count"] >= 55
    assert v2["unassigned_job_count"] >= 8

    # Verify persisted metrics endpoint on v2
    metrics_resp = client.get(f"/api/v1/schedules/{v2_id}/metrics")
    assert metrics_resp.status_code == 200
    m = metrics_resp.json()
    assert m["total_jobs_in_scope"] == 100
    assert m["hard_constraint_violations_count"] == 0
    assert m["technician_workload_distribution"]["technicians_evaluated"] == 18

    # Compare v1 and v2
    cmp_resp = client.get(f"/api/v1/schedules/{v1_id}/compare/{v2_id}")
    assert cmp_resp.status_code == 200
    assert cmp_resp.json()["deltas"]["assigned_jobs_delta"] >= 45

