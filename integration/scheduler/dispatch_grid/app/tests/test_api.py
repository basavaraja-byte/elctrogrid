"""FastAPI integration tests covering endpoints, schemas, validation, and error handling."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.routes.scheduling import InMemoryScheduleRunStore, get_schedule_store
from app.main import create_app


def test_health_and_before_first_run_404() -> None:
    client = TestClient(create_app())

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    cur = client.get("/api/v1/scheduling/current")
    assert cur.status_code == 404
    body = cur.json()
    assert body["error_code"] == "HTTP_404"


def test_audit_endpoint_and_unknown_scenario_error() -> None:
    client = TestClient(create_app())

    resp = client.get("/api/v1/scheduling/audit")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_electricians"] == 20
    assert data["total_jobs"] == 100
    assert data["static_eligibility_buckets"]["0"] == 1

    bad_scen = client.get("/api/v1/scheduling/audit?scenario_ids=D999")
    assert bad_scen.status_code == 400
    assert bad_scen.json()["error_code"] == "HTTP_400"


def test_generate_retrieve_metrics_explanations_and_optimize_workflow() -> None:
    app = create_app()
    custom_store = InMemoryScheduleRunStore()
    app.dependency_overrides[get_schedule_store] = lambda: custom_store
    client = TestClient(app)

    # 1. Generate greedy-only custom in-memory schedule first
    payload = {
        "run_id": "run-test-001",
        "use_bundled_dataset": False,
        "electricians": [
            {
                "technician_id": "E1",
                "name": "Tech 1",
                "trade": "electrician",
                "skills": ["fault_diagnosis"],
                "eligible_zones": ["Central"],
                "shift_start_min": 480,
                "shift_end_min": 960,
            },
            {
                "technician_id": "E2",
                "name": "Tech 2",
                "trade": "electrician",
                "skills": ["fault_diagnosis"],
                "eligible_zones": ["Central"],
                "shift_start_min": 480,
                "shift_end_min": 960,
            },
        ],
        "jobs": [
            {
                "job_id": "J1",
                "trade": "electrician",
                "required_skills": ["fault_diagnosis"],
                "priority": "High",
                "duration_min": 60,
                "zone": "Central",
                "window_start_min": 540,
                "window_end_min": 660,
                "sla_deadline_min": 780,
            },
            {
                "job_id": "J_NO_ZONE",
                "trade": "electrician",
                "required_skills": ["fault_diagnosis"],
                "priority": "Low",
                "duration_min": 45,
                "zone": "Mars_Zone",
                "window_start_min": 600,
                "window_end_min": 720,
                "sla_deadline_min": 840,
            },
        ],
        "travel_times": [
            {"from_location_id": "HOME_E1", "to_location_id": "J1", "travel_time_min": 25},
            {"from_location_id": "HOME_E2", "to_location_id": "J1", "travel_time_min": 10},
        ],
        "config": {"enable_optimization": False},
    }

    gen_resp = client.post("/api/v1/scheduling/generate", json=payload)
    assert gen_resp.status_code == 201
    gen_data = gen_resp.json()
    assert gen_data["run_id"] == "run-test-001"
    assert gen_data["is_valid_for_commitment"] is True
    assert gen_data["assigned_job_ids"] == ["J1"]
    assert gen_data["unassigned_job_ids"] == ["J_NO_ZONE"]
    assert gen_data["optimization"]["termination_reason"] == "OPTIMIZATION_DISABLED"

    # 2. Retrieve current & by run_id
    cur_resp = client.get("/api/v1/scheduling/current")
    assert cur_resp.status_code == 200
    assert cur_resp.json()["run_id"] == "run-test-001"

    by_id = client.get("/api/v1/scheduling/runs/run-test-001")
    assert by_id.status_code == 200

    # 3. Metrics & Explanations endpoints
    metrics_resp = client.get("/api/v1/scheduling/runs/run-test-001/metrics")
    assert metrics_resp.status_code == 200
    m_data = metrics_resp.json()
    assert m_data["total_travel_min"] == 10
    assert m_data["total_service_min"] == 60
    assert m_data["hard_constraint_violation_count"] == 0

    expl_resp = client.get("/api/v1/scheduling/runs/run-test-001/explanations")
    assert expl_resp.status_code == 200
    e_data = expl_resp.json()
    assert e_data["assigned_explanations"]["J1"]["selected_technician_id"] == "E2"
    assert e_data["unassigned_reasons"]["J_NO_ZONE"]["primary_reason_code"] == "ZONE_INELIGIBLE"

    # 4. Optimize stored run via POST /optimize
    opt_resp = client.post("/api/v1/scheduling/optimize", json={"run_id": "run-test-001"})
    assert opt_resp.status_code == 200
    opt_data = opt_resp.json()
    assert opt_data["optimization"]["enabled"] is True
    assert opt_data["is_valid_for_commitment"] is True


def test_request_validation_and_error_handling() -> None:
    client = TestClient(create_app())

    # Unknown extra field or negative weight triggers structured 422 VALIDATION_ERROR
    bad_cfg = client.post(
        "/api/v1/scheduling/generate",
        json={"config": {"w_travel": -1.0}},
    )
    assert bad_cfg.status_code == 422
    assert bad_cfg.json()["error_code"] == "VALIDATION_ERROR"

    # use_bundled_dataset=False without explicit lists triggers 400 HTTP_400
    missing_inputs = client.post(
        "/api/v1/scheduling/generate",
        json={"use_bundled_dataset": False},
    )
    assert missing_inputs.status_code == 400
    assert missing_inputs.json()["error_code"] == "HTTP_400"

    # Unknown run_id on optimize returns 404
    missing_run = client.post(
        "/api/v1/scheduling/optimize",
        json={"run_id": "nonexistent-run"},
    )
    assert missing_run.status_code == 404
    assert missing_run.json()["error_code"] == "HTTP_404"


def test_bundled_dataset_and_scenario_d02_via_api() -> None:
    client = TestClient(create_app())

    gen_resp = client.post(
        "/api/v1/scheduling/generate",
        json={
            "use_bundled_dataset": True,
            "scenario_ids": ["D02"],
            "include_dataset_audit": True,
        },
    )
    assert gen_resp.status_code == 201
    body = gen_resp.json()
    assert body["is_valid_for_commitment"] is True
    assert "J101" in body["assigned_job_ids"]
    assert body["dataset_audit"] is not None

    cur_metrics = client.get("/api/v1/scheduling/current/metrics")
    assert cur_metrics.status_code == 200
    assert cur_metrics.json()["hard_constraint_violation_count"] == 0

    cur_expl = client.get("/api/v1/scheduling/current/explanations")
    assert cur_expl.status_code == 200
    assert "J101" in cur_expl.json()["assigned_explanations"]
    assert "J100" in cur_expl.json()["unassigned_reasons"]


def test_dispatch_timeout_reject_retry_and_accept_api_workflow() -> None:
    client = TestClient(create_app())

    gen_payload = {
        "run_id": "run-dispatch-api",
        "use_bundled_dataset": False,
        "electricians": [
            {
                "technician_id": "E1",
                "name": "Tech 1",
                "trade": "electrician",
                "skills": ["fault_diagnosis"],
                "eligible_zones": ["Central"],
                "shift_start_min": 480,
                "shift_end_min": 960,
            },
            {
                "technician_id": "E2",
                "name": "Tech 2",
                "trade": "electrician",
                "skills": ["fault_diagnosis"],
                "eligible_zones": ["Central"],
                "shift_start_min": 480,
                "shift_end_min": 960,
            },
        ],
        "jobs": [
            {
                "job_id": "J1",
                "trade": "electrician",
                "required_skills": ["fault_diagnosis"],
                "priority": "High",
                "duration_min": 60,
                "zone": "Central",
                "window_start_min": 540,
                "window_end_min": 660,
                "sla_deadline_min": 780,
            }
        ],
        "travel_times": [
            {"from_location_id": "HOME_E1", "to_location_id": "J1", "travel_time_min": 10},
            {"from_location_id": "HOME_E2", "to_location_id": "J1", "travel_time_min": 25},
        ],
        "config": {"enable_optimization": False},
    }
    assert client.post("/api/v1/scheduling/generate", json=gen_payload).status_code == 201

    init_resp = client.post(
        "/api/v1/scheduling/dispatch/runs/run-dispatch-api/init",
        json={"auto_offer_all": True, "now_utc": "2026-05-04T08:00:00Z"},
    )
    assert init_resp.status_code == 201
    init_body = init_resp.json()
    assert init_body["pending_offer_count"] == 1
    off1 = init_body["job_states"]["J1"]["offers"][0]
    assert off1["technician_id"] == "E1"

    # E1 misses the 5-minute deadline -> sweep-timeouts at +300s retries E2
    sweep_resp = client.post(
        "/api/v1/scheduling/dispatch/runs/run-dispatch-api/sweep-timeouts",
        json={"now_utc": "2026-05-04T08:05:00Z"},
    )
    assert sweep_resp.status_code == 200
    sweep_body = sweep_resp.json()
    assert sweep_body["timed_out_offer_ids"] == [off1["offer_id"]]
    assert len(sweep_body["new_offers"]) == 1
    off2 = sweep_body["new_offers"][0]
    assert off2["technician_id"] == "E2"

    # Stale response from E1 on timed-out off1 returns HTTP 409 Conflict
    stale_resp = client.post(
        "/api/v1/scheduling/dispatch/runs/run-dispatch-api/respond",
        json={
            "offer_id": off1["offer_id"],
            "technician_id": "E1",
            "decision": "accept",
            "responded_at_utc": "2026-05-04T08:05:10Z",
        },
    )
    assert stale_resp.status_code == 409

    # E2 accepts off2 within its 5-minute window
    acc_resp = client.post(
        "/api/v1/scheduling/dispatch/runs/run-dispatch-api/respond",
        json={
            "offer_id": off2["offer_id"],
            "technician_id": "E2",
            "decision": "accept",
            "responded_at_utc": "2026-05-04T08:06:00Z",
        },
    )
    assert acc_resp.status_code == 200
    assert acc_resp.json()["state"]["accepted_count"] == 1
    assert acc_resp.json()["state"]["is_valid_for_commitment"] is True


def test_recovery_scenarios_and_idempotency_api_endpoints() -> None:
    client = TestClient(create_app())

    scen_resp = client.get("/api/v1/scheduling/recovery/scenarios")
    assert scen_resp.status_code == 200
    assert sorted(scen_resp.json().keys()) == ["D01", "D02", "D03", "D04", "D05", "D06", "D07"]

    # Simulate D06 with an explicit API idempotency_key
    sim1 = client.post(
        "/api/v1/scheduling/recovery/simulate",
        json={"scenario_id": "D06", "idempotency_key": "api-idem-d06"},
    )
    assert sim1.status_code == 200
    body1 = sim1.json()
    assert body1["validation_passed"] is True
    assert body1["objective_consistent"] is True
    assert body1["duplicate_request_suppressed"] is True
    assert body1["idempotent_replay"] is False

    # Replay same idempotency_key -> idempotent_replay=True
    sim2 = client.post(
        "/api/v1/scheduling/recovery/simulate",
        json={"scenario_id": "D06", "idempotency_key": "api-idem-d06"},
    )
    assert sim2.status_code == 200
    assert sim2.json()["idempotent_replay"] is True

    # Reuse same idempotency_key for a different scenario -> 409 Conflict
    conflict = client.post(
        "/api/v1/scheduling/recovery/simulate",
        json={"scenario_id": "D07", "idempotency_key": "api-idem-d06"},
    )
    assert conflict.status_code == 409


