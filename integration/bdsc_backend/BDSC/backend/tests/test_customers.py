"""Tests for the external Customer (Client) model, Swagger UI examples, validation, and Customer-Job integration."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.schemas.customer import CUSTOMER_EXAMPLE
from app.schemas.job import JOB_CREATE_EXAMPLE
from app.schemas.technician import TECHNICIAN_EXAMPLE

IST = timezone(timedelta(hours=5, minutes=30))


def test_swagger_ui_default_examples_succeed(client: TestClient) -> None:
    """Verify the exact Swagger UI json_schema_extra example payloads succeed with 201 Created."""
    cust_res = client.post("/api/v1/customers", json=CUSTOMER_EXAMPLE)
    assert cust_res.status_code == 201, cust_res.text

    job_res = client.post("/api/v1/jobs", json=JOB_CREATE_EXAMPLE)
    assert job_res.status_code == 201, job_res.text

    tech_res = client.post("/api/v1/technicians", json=TECHNICIAN_EXAMPLE)
    assert tech_res.status_code == 201, tech_res.text


def test_create_individual_customer_without_email(client: TestClient) -> None:
    """Verify an INDIVIDUAL customer can be created without an email and gets a unique customer_code."""
    payload = {
        "full_name": "Rohan Kulkarni",
        "email": None,
        "phone_number": "+91-9845012345",
        "alternate_phone_number": None,
        "customer_type": "INDIVIDUAL",
        "company_name": None,
        "service_address": "Flat 302, Green Valley Apartments, Jayanagar 4th Block",
        "city": "Bengaluru",
        "state": "Karnataka",
        "postal_code": "560041",
        "latitude": 12.9255,
        "longitude": 77.5942,
        "is_active": True,
    }
    res = client.post("/api/v1/customers", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["id"] is not None
    assert data["customer_code"].startswith("CUST-")
    assert data["full_name"] == "Rohan Kulkarni"
    assert data["email"] is None
    assert data["phone_number"] == "+91-9845012345"
    assert data["customer_type"] == "INDIVIDUAL"
    assert data["is_active"] is True
    assert "password" not in data


def test_create_business_customer_with_email_and_unique_codes(client: TestClient) -> None:
    """Verify BUSINESS customer creation, email normalization, and unique customer_code generation."""
    payload_1 = {
        "full_name": "Meera Reddy",
        "email": "Facilities@ApexTechPark.in",
        "phone_number": "+91 80 4090 1122",
        "alternate_phone_number": "+91-9900112233",
        "customer_type": "BUSINESS",
        "company_name": "Apex Tech Park Pvt Ltd",
        "service_address": "Plot 14, EPIP Zone Phase 2, Whitefield",
        "city": "Bengaluru",
        "state": "Karnataka",
        "postal_code": "560066",
        "latitude": 12.9710,
        "longitude": 77.7510,
    }
    res1 = client.post("/api/v1/customers", json=payload_1)
    assert res1.status_code == 201, res1.text
    c1 = res1.json()
    assert c1["email"] == "facilities@apextechpark.in"
    assert c1["customer_type"] == "BUSINESS"
    assert c1["company_name"] == "Apex Tech Park Pvt Ltd"

    res2 = client.post("/api/v1/customers", json=payload_1)
    assert res2.status_code == 201, res2.text
    c2 = res2.json()
    assert c1["customer_code"] != c2["customer_code"]
    assert c1["id"] != c2["id"]

    # Retrieve by customer_code
    by_code = client.get(f"/api/v1/customers/by-code/{c1['customer_code']}")
    assert by_code.status_code == 200
    assert by_code.json()["id"] == c1["id"]


def test_customer_missing_required_fields_and_invalid_types(client: TestClient) -> None:
    """Verify missing required fields and invalid field types return 422 with field details."""
    # Missing required fields
    missing_res = client.post("/api/v1/customers", json={"full_name": "Only Name"})
    assert missing_res.status_code == 422
    body = missing_res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    missing_fields = {item["field"] for item in body["error"]["details"]}
    assert "phone_number" in missing_fields
    assert "service_address" in missing_fields
    assert "latitude" in missing_fields

    # Invalid field types (latitude as non-numeric string)
    bad_type_res = client.post(
        "/api/v1/customers",
        json={**CUSTOMER_EXAMPLE, "latitude": "not-a-float"},
    )
    assert bad_type_res.status_code == 422
    assert bad_type_res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_uuids_and_invalid_enums_rejected(client: TestClient) -> None:
    """Verify invalid UUIDs and invalid enum values return 422 Unprocessable Content."""
    # Invalid UUID in path
    bad_path_uuid = client.get("/api/v1/customers/not-a-valid-uuid")
    assert bad_path_uuid.status_code == 422
    assert bad_path_uuid.json()["error"]["code"] == "VALIDATION_ERROR"

    # Invalid UUID in job customer_id field
    bad_job_cust_uuid = client.post(
        "/api/v1/jobs",
        json={**JOB_CREATE_EXAMPLE, "customer_id": "invalid-uuid-format"},
    )
    assert bad_job_cust_uuid.status_code == 422
    assert bad_job_cust_uuid.json()["error"]["code"] == "VALIDATION_ERROR"

    # Invalid enum for customer_type
    bad_enum_cust = client.post(
        "/api/v1/customers",
        json={**CUSTOMER_EXAMPLE, "customer_type": "GOVERNMENT_ENTITY"},
    )
    assert bad_enum_cust.status_code == 422
    assert bad_enum_cust.json()["error"]["code"] == "VALIDATION_ERROR"

    # Invalid enum for job priority
    bad_enum_job = client.post(
        "/api/v1/jobs",
        json={**JOB_CREATE_EXAMPLE, "priority": "SUPER_URGENT"},
    )
    assert bad_enum_job.status_code == 422
    assert bad_enum_job.json()["error"]["code"] == "VALIDATION_ERROR"


def test_customer_email_and_phone_validation_rejects_invalid_formats(client: TestClient) -> None:
    """Verify invalid email or phone number formats are rejected with 422."""
    invalid_email_payload = {
        **CUSTOMER_EXAMPLE,
        "email": "not-an-email-address",
    }
    res_email = client.post("/api/v1/customers", json=invalid_email_payload)
    assert res_email.status_code == 422

    invalid_phone_payload = {
        **CUSTOMER_EXAMPLE,
        "phone_number": "123",
    }
    res_phone = client.post("/api/v1/customers", json=invalid_phone_payload)
    assert res_phone.status_code == 422


def test_duplicate_customer_code_constraint_violation_returns_409(client: TestClient) -> None:
    """Verify duplicate customer_code returns 409 Conflict."""
    payload = {**CUSTOMER_EXAMPLE, "customer_code": "CUST-CUSTOM99"}
    res1 = client.post("/api/v1/customers", json=payload)
    assert res1.status_code == 201
    assert res1.json()["customer_code"] == "CUST-CUSTOM99"

    res2 = client.post("/api/v1/customers", json=payload)
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "DUPLICATE_CUSTOMER_CODE"


def test_customer_job_linking_auto_populates_and_filters(client: TestClient) -> None:
    """Verify linking a Job to a Customer auto-populates customer_name/contact when omitted and supports filtering."""
    cust_res = client.post(
        "/api/v1/customers",
        json={
            "full_name": "Deepak Shenoy",
            "email": "deepak.shenoy@example.org",
            "phone_number": "+91-9880011223",
            "customer_type": "INDIVIDUAL",
            "service_address": "45 100ft Road, Koramangala",
            "city": "Bengaluru",
            "state": "Karnataka",
            "postal_code": "560034",
            "latitude": 12.9352,
            "longitude": 77.6245,
        },
    )
    assert cust_res.status_code == 201
    customer = cust_res.json()

    ws = datetime(2026, 10, 30, 10, 0, tzinfo=IST)
    we = ws + timedelta(hours=2)
    sla = ws + timedelta(hours=3)

    # Create job referencing customer_id WITHOUT explicitly passing customer_name
    job_res = client.post(
        "/api/v1/jobs",
        json={
            "customer_id": customer["id"],
            "job_type": "Wiring repair",
            "description": "Repair residential circuit wiring",
            "required_skills": ["Residential wiring"],
            "priority": "HIGH",
            "latitude": customer["latitude"],
            "longitude": customer["longitude"],
            "service_zone": "BLR-SE-KORAMANGALA",
            "estimated_duration_minutes": 60,
            "appointment_window_start": ws.isoformat(),
            "appointment_window_end": we.isoformat(),
            "sla_deadline": sla.isoformat(),
        },
    )
    assert job_res.status_code == 201, job_res.text
    job = job_res.json()
    assert job["customer_id"] == customer["id"]
    assert job["customer_name"] == "Deepak Shenoy"
    assert job["customer_contact"] == "+91-9880011223"

    # Query via GET /api/v1/customers/{id}/jobs
    cust_jobs_res = client.get(f"/api/v1/customers/{customer['id']}/jobs")
    assert cust_jobs_res.status_code == 200
    cust_jobs = cust_jobs_res.json()
    assert len(cust_jobs) == 1
    assert cust_jobs[0]["id"] == job["id"]

    # Query via GET /api/v1/jobs?customer_id=...
    filtered_jobs_res = client.get("/api/v1/jobs", params={"customer_id": customer["id"]})
    assert filtered_jobs_res.status_code == 200
    assert len(filtered_jobs_res.json()) == 1
    assert filtered_jobs_res.json()[0]["id"] == job["id"]

    # Toggle customer status
    patch_res = client.patch(
        f"/api/v1/customers/{customer['id']}/status",
        json={"is_active": False, "reason": "Account deactivated by request"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["is_active"] is False
