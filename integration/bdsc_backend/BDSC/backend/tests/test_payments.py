"""Comprehensive Unit and Integration Tests for Billing, Actual Duration,
Damaged Components, Invoicing, Cash Settlement, and Razorpay Verification.
"""

from datetime import datetime, timedelta, timezone
import math
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import JobPriority, JobStatus
from app.models.job import Job
from app.services.payment_service import (
    calculate_duration_from_timestamps,
    calculate_service_billing,
)
from app.services.pdf_service import generate_invoice_pdf


# ============================================================================
# MODULE 1 TESTS — TIME-BASED SERVICE PRICING SLABS (MANDATORY EXAMPLES)
# ============================================================================

@pytest.mark.parametrize(
    "minutes,expected_inr,expected_blocks",
    [
        (1, 500, 0),
        (30, 500, 0),
        (60, 500, 0),
        (61, 600, 1),
        (75, 600, 1),
        (89, 600, 1),
        (90, 600, 1),
        (91, 700, 2),
        (120, 700, 2),
        (121, 800, 3),
        (150, 800, 3),
        (151, 900, 4),
        (180, 900, 4),
    ],
)
def test_time_based_pricing_exact_slabs(minutes: int, expected_inr: int, expected_blocks: int):
    """Test every mandatory billing duration example required by Module 1 & Module 14."""
    calc = calculate_service_billing(minutes)
    assert calc.labour_total_inr == expected_inr
    assert calc.labour_total_paise == expected_inr * 100
    assert calc.base_amount_inr == 500
    assert calc.base_amount_paise == 50000
    assert calc.additional_blocks == expected_blocks
    assert calc.additional_amount_inr == expected_blocks * 100
    assert calc.additional_amount_paise == expected_blocks * 10000
    assert calc.currency == "INR"


# ============================================================================
# MODULE 2 TESTS — DURATION CALCULATION & TIMESTAMP ROUNDING
# ============================================================================

def test_duration_rounding_up_seconds():
    """Verify elapsed seconds are rounded UP to next whole minute before slabs."""
    t_start = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc)
    # 60 minutes and 1 second -> should round to 61 minutes -> ₹600
    t_end_61 = t_start + timedelta(minutes=60, seconds=1)
    duration_61 = calculate_duration_from_timestamps(t_start, t_end_61)
    assert duration_61 == 61
    calc_61 = calculate_service_billing(duration_61)
    assert calc_61.labour_total_inr == 600

    # 59 minutes and 59 seconds -> should round to 60 minutes -> ₹500
    t_end_60 = t_start + timedelta(minutes=59, seconds=59)
    duration_60 = calculate_duration_from_timestamps(t_start, t_end_60)
    assert duration_60 == 60
    calc_60 = calculate_service_billing(duration_60)
    assert calc_60.labour_total_inr == 500


# ============================================================================
# MODULE 8 TESTS — PDF GENERATION & FORMATTING
# ============================================================================

def test_pdf_receipt_generation():
    """Verify ReportLab PDF generation builds cleanly with required sections."""
    invoice_number = f"EG-2026-T{uuid.uuid4().hex[:6]}"
    url = generate_invoice_pdf(
        invoice_number=invoice_number,
        invoice_date=datetime.now(timezone.utc),
        customer_name="Ananya Rao",
        job_reference="JOB-2026-TEST",
        technician_name="Guruprasad Rao",
        service_description="High-voltage switchgear inspection",
        duration_minutes=75,
        base_amount_inr=500,
        additional_blocks=1,
        additional_amount_inr=100,
        labour_total_inr=600,
        payment_method="CASH",
        payment_status="PAID",
        payment_reference="PAY-TEST-RECEIPT",
        damaged_components=[
            {
                "component_name": "Main Contactor 40A",
                "damage_description": "Contact pitting and oxidation",
                "quantity": 1,
                "price_status": "Price to be confirmed",
            }
        ],
    )
    assert url.endswith(f"{invoice_number}.pdf")


# ============================================================================
# API ENDPOINT TESTS (CORS, CONFIG, ORDERS, FAILURE)
# ============================================================================

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
        "amount_inr": 600.0,
    }
    resp = client.post("/api/v1/payments/orders", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["booking_code"] == "JOB-2026-4011"
    assert data["amount_paise"] == 60000
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


# ============================================================================
# MODULE 14 TESTS — COMPLETE END-TO-END WORKFLOW INTEGRATION
# ============================================================================

def test_full_job_completion_cash_and_invoice_workflow(client: TestClient, db_session: Session):
    """Test full workflow:
    1. Start job (record actual_start_time)
    2. Complete job with damaged components (calculate duration & bill, PENDING)
    3. Customer payment request verification
    4. Customer selects Cash (instructions, PENDING)
    5. Customer forbidden from confirming cash
    6. Technician confirms cash (updates to PAID, generates receipt)
    7. PDF receipt download
    8. Idempotency on repeated confirmation
    """
    now_utc = datetime.now(timezone.utc)
    job = Job(
        customer_name="Ananya Rao",
        customer_contact="+91 98450 21001",
        job_type="breaker_replacement",
        description="Circuit breaker overheating and tripping",
        required_skills=["Residential wiring"],
        priority="HIGH",
        status=JobStatus.ASSIGNED.value,
        latitude=12.2958,
        longitude=76.6394,
        service_zone="ZONE_SOUTH_COUNTY",
        estimated_duration_minutes=60,
        appointment_window_start=now_utc,
        appointment_window_end=now_utc + timedelta(hours=2),
        sla_deadline=now_utc + timedelta(hours=3),
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    job_id_str = str(job.id)

    # 1. Start Job
    start_resp = client.post(f"/api/v1/payments/jobs/{job_id_str}/start")
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["status"] == "IN_PROGRESS"
    assert start_data["actual_start_time"] is not None

    # Simulate 75 minutes of work by updating actual_start_time in DB
    job.actual_start_time = datetime.now(timezone.utc) - timedelta(minutes=75, seconds=5)
    db_session.commit()

    # 2. Complete Job with Damaged Components
    complete_payload = {
        "work_summary": "Replaced faulty 60A dual-pole breaker, torqued screws to spec.",
        "damaged_components": [
            {
                "component_name": "60A Dual-Pole Breaker",
                "damage_description": "Terminal heat degradation and carbon arc pitting",
                "quantity": 1,
                "price_status": "Price to be confirmed",
            }
        ],
    }
    comp_resp = client.post(
        f"/api/v1/payments/jobs/{job_id_str}/complete?technician_name=Guruprasad+Rao",
        json=complete_payload,
    )
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    # 75 minutes + 5 sec -> rounds to 76 minutes -> (76-60)/30 = ceil(16/30) = 1 block -> ₹600
    assert comp_data["base_amount_inr"] == 500
    assert comp_data["additional_blocks"] == 1
    assert comp_data["additional_amount_inr"] == 100
    assert comp_data["labour_total_inr"] == 600
    assert comp_data["payment_status"] == "PENDING"
    assert len(comp_data["damaged_components"]) == 1
    assert comp_data["damaged_components"][0]["price_status"] == "Price to be confirmed"

    # 3. Customer retrieves Payment Request
    get_resp = client.get(f"/api/v1/payments/jobs/{job_id_str}")
    assert get_resp.status_code == 200
    assert get_resp.json()["labour_total_inr"] == 600

    # 4. Customer initiates Cash Payment
    cash_init_resp = client.post(f"/api/v1/payments/jobs/{job_id_str}/cash/initiate")
    assert cash_init_resp.status_code == 200
    assert cash_init_resp.json()["amount_due_inr"] == 600
    assert cash_init_resp.json()["payment_status"] == "PENDING"

    # 5. Customer is forbidden from self-confirming cash
    forbidden_resp = client.post(
        f"/api/v1/payments/jobs/{job_id_str}/cash/confirm",
        json={"job_id": job_id_str, "confirmed_by_name": "Ananya Rao", "confirmed_by_role": "customer"},
    )
    assert forbidden_resp.status_code == 403

    # 6. Technician confirms Cash
    confirm_resp = client.post(
        f"/api/v1/payments/jobs/{job_id_str}/cash/confirm",
        json={"job_id": job_id_str, "confirmed_by_name": "Guruprasad Rao", "confirmed_by_role": "technician"},
    )
    assert confirm_resp.status_code == 200
    confirm_data = confirm_resp.json()
    assert confirm_data["payment_status"] == "PAID"
    assert confirm_data["payment_method"] == "CASH"
    assert confirm_data["invoice_number"].startswith("EG-")
    assert confirm_data["invoice"]["pdf_url"] is not None

    # 7. Customer / Technician downloads PDF receipt
    inv_num = confirm_data["invoice_number"]
    pdf_resp = client.get(f"/api/v1/payments/invoices/{inv_num}/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert len(pdf_resp.content) > 1000

    # 8. Idempotency: Repeating confirmation returns existing receipt
    repeat_resp = client.post(
        f"/api/v1/payments/jobs/{job_id_str}/cash/confirm",
        json={"job_id": job_id_str, "confirmed_by_name": "Guruprasad Rao", "confirmed_by_role": "technician"},
    )
    assert repeat_resp.status_code == 200
    assert repeat_resp.json()["invoice_number"] == inv_num
