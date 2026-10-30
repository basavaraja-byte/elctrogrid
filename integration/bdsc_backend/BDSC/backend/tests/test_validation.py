"""Tests for domain validation rules, error response envelope, and centralized ConstraintValidator."""

from fastapi.testclient import TestClient

from tests.test_jobs import _sample_job_payload, _sample_tech_payload


def test_invalid_duration_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/jobs",
        json=_sample_job_payload(estimated_duration_minutes=-15),
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_appointment_window_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/jobs",
        json=_sample_job_payload(
            appointment_window_start="2026-10-30T14:00:00+05:30",
            appointment_window_end="2026-10-30T10:00:00+05:30",
        ),
    )
    assert resp.status_code == 422
    assert resp.json()["success"] is False


def test_invalid_coordinates_rejected(client: TestClient) -> None:
    resp_job = client.post(
        "/api/v1/jobs",
        json=_sample_job_payload(latitude=125.0, longitude=77.59),
    )
    assert resp_job.status_code == 422

    resp_tech = client.post(
        "/api/v1/technicians",
        json=_sample_tech_payload(latitude=12.97, longitude=220.0),
    )
    assert resp_tech.status_code == 422


def test_missing_required_fields_rejected(client: TestClient) -> None:
    resp = client.post("/api/v1/jobs", json={"customer_name": "Incomplete"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert len(body["error"]["details"]) > 0


def test_empty_required_skills_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/jobs",
        json=_sample_job_payload(required_skills=[]),
    )
    assert resp.status_code == 422


def test_shift_policy_rejects_inverted_or_zero_shift(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/technicians",
        json=_sample_tech_payload(shift_start="17:00:00", shift_end="08:00:00"),
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["success"] is False


def test_inactive_technician_cannot_receive_job_assignment(client: TestClient) -> None:
    t_resp = client.post(
        "/api/v1/technicians",
        json=_sample_tech_payload(is_active=False),
    )
    tech_id = t_resp.json()["id"]

    j_resp = client.post(
        "/api/v1/jobs",
        json=_sample_job_payload(assigned_technician_id=tech_id),
    )
    assert j_resp.status_code == 400
    assert j_resp.json()["error"]["code"] == "INACTIVE_TECHNICIAN"

