"""Tests for Technician CRUD APIs, filters, and time-aware availability checks."""

import uuid
from fastapi.testclient import TestClient


def _sample_technician_payload(**overrides) -> dict:
    base = {
        "name": "Ramesh Gowda",
        "phone": "+91-9845011223",
        "skills": [
            "Residential wiring",
            "Circuit breaker repair",
            "Distribution board maintenance",
        ],
        "service_zones": ["BLR-SOUTH-JAYANAGAR", "BLR-SE-KORAMANGALA"],
        "latitude": 12.9250,
        "longitude": 77.5938,
        "shift_start": "08:00:00",
        "shift_end": "17:00:00",
        "is_active": True,
        "availability_status": "AVAILABLE",
        "unavailable_windows": [
            {
                "start": "2026-10-30T13:00:00+05:30",
                "end": "2026-10-30T13:30:00+05:30",
                "status": "ON_BREAK",
                "reason": "Lunch break",
            }
        ],
    }
    base.update(overrides)
    return base


def test_create_and_retrieve_technician(client: TestClient) -> None:
    resp = client.post("/api/v1/technicians", json=_sample_technician_payload())
    assert resp.status_code == 201
    created = resp.json()
    assert created["name"] == "Ramesh Gowda"
    assert created["availability_status"] == "AVAILABLE"
    assert len(created["unavailable_windows"]) == 1

    tech_id = created["id"]
    get_resp = client.get(f"/api/v1/technicians/{tech_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == tech_id


def test_list_technicians_with_filters_and_time_window(client: TestClient) -> None:
    client.post("/api/v1/technicians", json=_sample_technician_payload())
    client.post(
        "/api/v1/technicians",
        json=_sample_technician_payload(
            name="Mahesh OffDuty",
            skills=["Industrial wiring"],
            service_zones=["BLR-NORTH-HEBBAL"],
            availability_status="OFF_DUTY",
        ),
    )

    # Filter by skill
    r_skill = client.get("/api/v1/technicians", params={"skill": "Industrial wiring"})
    assert r_skill.status_code == 200
    assert len(r_skill.json()) == 1
    assert r_skill.json()[0]["name"] == "Mahesh OffDuty"

    # Filter by time-aware availability during Ramesh's lunch break (13:00 - 13:30)
    r_lunch = client.get(
        "/api/v1/technicians",
        params={
            "service_zone": "BLR-SOUTH-JAYANAGAR",
            "available_from": "2026-10-30T13:05:00+05:30",
            "available_until": "2026-10-30T13:25:00+05:30",
        },
    )
    assert r_lunch.status_code == 200
    assert len(r_lunch.json()) == 0

    # Filter by time-aware availability during morning shift (09:00 - 10:00)
    r_morning = client.get(
        "/api/v1/technicians",
        params={
            "service_zone": "BLR-SOUTH-JAYANAGAR",
            "available_from": "2026-10-30T09:00:00+05:30",
            "available_until": "2026-10-30T10:00:00+05:30",
        },
    )
    assert r_morning.status_code == 200
    assert len(r_morning.json()) == 1


def test_patch_technician_availability_and_check_endpoint(client: TestClient) -> None:
    resp = client.post("/api/v1/technicians", json=_sample_technician_payload())
    tech_id = resp.json()["id"]

    # Check window outside shift -> OFF_DUTY
    check_off = client.get(
        f"/api/v1/technicians/{tech_id}/availability-check",
        params={
            "window_start": "2026-10-30T19:00:00+05:30",
            "window_end": "2026-10-30T20:00:00+05:30",
        },
    )
    assert check_off.status_code == 200
    assert check_off.json()["is_available"] is False
    assert check_off.json()["effective_status"] == "OFF_DUTY"

    # Patch availability to ON_BREAK and add a new unavailable window
    patch_resp = client.patch(
        f"/api/v1/technicians/{tech_id}/availability",
        json={
            "availability_status": "ON_BREAK",
            "unavailable_window": {
                "start": "2026-10-30T15:00:00+05:30",
                "end": "2026-10-30T16:00:00+05:30",
                "status": "UNAVAILABLE",
                "reason": "Equipment calibration",
            },
            "reason": "Scheduled calibration",
        },
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["availability_status"] == "ON_BREAK"
    assert len(patch_resp.json()["unavailable_windows"]) == 2


def test_missing_technician_returns_404(client: TestClient) -> None:
    missing_id = uuid.uuid4()
    resp = client.get(f"/api/v1/technicians/{missing_id}")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"

