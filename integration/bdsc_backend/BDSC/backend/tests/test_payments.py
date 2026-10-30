"""Unit tests for Razorpay payment integration in DispatchGrid."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_payment_config(client: TestClient):
    """Test payment config endpoint returns test mode configuration."""
    resp = client.get("/api/v1/payments/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["payment_mode"] == "test"
    assert data["currency"] == "INR"
    assert data["demo_payment_enabled"] is True


def test_create_payment_order(client: TestClient):
    """Test Razorpay order creation returns valid order attributes."""
    payload = {
        "booking_code": "JOB-2026-4011",
        "amount_inr": 1120.0,
    }
    resp = client.post("/api/v1/payments/orders", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["booking_code"] == "JOB-2026-4011"
    assert data["amount_paise"] == 112000
    assert data["currency"] == "INR"
    assert data["razorpay_order_id"].startswith("order_")
    assert data["payment_code"].startswith("PAY-")


def test_demo_simulate_payment(client: TestClient):
    """Test simulated sandbox payment endpoint."""
    payload = {
        "booking_code": "JOB-2026-4011",
        "acknowledge_simulation": True,
    }
    resp = client.post("/api/v1/payments/demo-simulate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["booking_code"] == "JOB-2026-4011"
    assert data["payment_status"] == "COMPLETED"
    assert data["is_demo_simulation"] is True
    assert data["razorpay_payment_id"].startswith("pay_test_sim_")


def test_record_payment_failure(client: TestClient):
    """Test recording a customer-cancelled or failed checkout event."""
    payload = {
        "booking_code": "JOB-2026-4011",
        "reason": "Customer dismissed checkout modal before OTP entry",
    }
    resp = client.post("/api/v1/payments/failure", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["payment_status"] == "FAILED"
    assert "dismissed checkout modal" in data["message"]

