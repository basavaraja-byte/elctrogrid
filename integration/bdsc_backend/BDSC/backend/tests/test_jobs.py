"""Tests for Job CRUD APIs, filters, status transitions, and immutability protection."""

import uuid
from fastapi.testclient import TestClient


def _sample_job_payload(**overrides) -> dict:
    base = {
        "customer_name": "Kalyani Motors Workshop",
        "customer_contact": "+91-80-40921001",
        "job_type": "Distribution board maintenance",
        "description": "3-phase main distribution board thermal trip inspection",
        "required_skills": ["Distribution board maintenance", "Circuit breaker repair"],
        "priority": "HIGH",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "service_zone": "BLR-CENTRAL-MG-ROAD",
        "estimated_duration_minutes": 60,
        "appointment_window_start": "2026-10-30T09:00:00+05:30",
        "appointment_window_end": "2026-10-30T13:00:00+05:30",
        "sla_deadline": "2026-10-30T14:00:00+05:30",
    }
    base.update(overrides)
    return base


def _sample_tech_payload(**overrides) -> dict:
    base = {
        "name": "Raghavendra Rao",
        "phone": "+91-9845012345",
        "skills": [
            "Distribution board maintenance",
            "Circuit breaker repair",
            "Electrical fault diagnosis",
        ],
        "service_zones": ["BLR-CENTRAL-MG-ROAD"],
        "latitude": 12.9716,
        "longitude": 77.5946,
        "shift_start": "08:00:00",
        "shift_end": "17:00:00",
        "is_active": True,
        "availability_status": "AVAILABLE",
    }
    base.update(overrides)
    return base


def test_create_retrieve_and_filter_jobs(client: TestClient) -> None:
    resp = client.post("/api/v1/jobs", json=_sample_job_payload())
    assert resp.status_code == 201
    job = resp.json()
    assert job["customer_name"] == "Kalyani Motors Workshop"
    assert job["status"] == "PENDING"

    job_id = job["id"]
    get_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == job_id

    # Filter by required_skill and priority
    list_resp = client.get(
        "/api/v1/jobs",
        params={"priority": "HIGH", "required_skill": "Circuit breaker repair"},
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


def test_job_status_lifecycle_and_immutability_protection(client: TestClient) -> None:
    t_resp = client.post("/api/v1/technicians", json=_sample_tech_payload())
    tech_id = t_resp.json()["id"]

    j_resp = client.post("/api/v1/jobs", json=_sample_job_payload())
    job_id = j_resp.json()["id"]

    # PENDING -> ASSIGNED
    r_assign = client.patch(
        f"/api/v1/jobs/{job_id}/status",
        json={"status": "ASSIGNED", "assigned_technician_id": tech_id},
    )
    assert r_assign.status_code == 200
    assert r_assign.json()["status"] == "ASSIGNED"

    # ASSIGNED -> IN_PROGRESS
    r_prog = client.patch(
        f"/api/v1/jobs/{job_id}/status",
        json={
            "status": "IN_PROGRESS",
            "actual_start_time": "2026-10-30T09:30:00+05:30",
        },
    )
    assert r_prog.status_code == 200
    assert r_prog.json()["status"] == "IN_PROGRESS"

    # Mandatory Addition #5: Cannot PUT/modify or DELETE an IN_PROGRESS job
    put_attempt = client.put(f"/api/v1/jobs/{job_id}", json=_sample_job_payload())
    assert put_attempt.status_code == 409
    assert put_attempt.json()["error"]["code"] == "IMMUTABLE_JOB_VIOLATION"

    del_attempt = client.delete(f"/api/v1/jobs/{job_id}")
    assert del_attempt.status_code == 409
    assert del_attempt.json()["error"]["code"] == "IMMUTABLE_JOB_VIOLATION"

    # IN_PROGRESS -> COMPLETED
    r_comp = client.patch(
        f"/api/v1/jobs/{job_id}/status",
        json={
            "status": "COMPLETED",
            "actual_completion_time": "2026-10-30T10:30:00+05:30",
        },
    )
    assert r_comp.status_code == 200
    assert r_comp.json()["status"] == "COMPLETED"

    # COMPLETED is terminal: cannot transition back to PENDING or IN_PROGRESS
    invalid_trans = client.patch(
        f"/api/v1/jobs/{job_id}/status",
        json={"status": "PENDING"},
    )
    assert invalid_trans.status_code == 400
    assert invalid_trans.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_missing_job_returns_404(client: TestClient) -> None:
    resp = client.get(f"/api/v1/jobs/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"

