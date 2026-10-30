"""Unit tests for Server-Side Role-Based Access Control and Supabase Token Verification."""

import base64
import json
import pytest
from fastapi import Depends, HTTPException
from fastapi.testclient import TestClient

from app.core.auth import (
    AppRole,
    AuthenticatedUser,
    get_current_user,
    parse_and_verify_token,
    require_role,
)
from app.main import app

client = TestClient(app)


def test_parse_demo_tokens():
    """Verify demo token parsing resolves correct server roles."""
    sup = parse_and_verify_token("mock-jwt-token-usr-sup-1")
    assert sup.role == AppRole.SUPERVISOR
    assert sup.email == "supervisor@dispatchgrid.io"

    tech = parse_and_verify_token("mock-jwt-token-usr-tech-1")
    assert tech.role == AppRole.TECHNICIAN

    cust = parse_and_verify_token("mock-jwt-token-usr-cust-ind-1")
    assert cust.role == AppRole.CUSTOMER


def test_parse_supabase_jwt():
    """Verify Supabase JWT claims are extracted and mapped to canonical roles."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload_data = {
        "sub": "b2f6762e-3c22-4412-9c10-09e9db639c0a",
        "email": "priya.sharma@dispatchgrid.in",
        "app_metadata": {"role": "supervisor"},
        "user_metadata": {"full_name": "Priya Sharma"},
    }
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
    signature = "fake_signature_for_test"
    fake_jwt = f"{header}.{payload}.{signature}"

    user = parse_and_verify_token(fake_jwt)
    assert user.role == AppRole.SUPERVISOR
    assert user.email == "priya.sharma@dispatchgrid.in"
    assert user.user_id == "b2f6762e-3c22-4412-9c10-09e9db639c0a"


def test_role_enforcement_rejects_unauthorized():
    """Verify require_role raises HTTP 403 when user lacks required role."""
    cust_user = AuthenticatedUser(
        user_id="cust-1",
        email="kiran@gmail.com",
        role=AppRole.CUSTOMER,
    )
    supervisor_checker = require_role([AppRole.SUPERVISOR])

    with pytest.raises(HTTPException) as exc_info:
        supervisor_checker(user=cust_user)

    assert exc_info.value.status_code == 403
    assert "Access denied" in exc_info.value.detail


def test_role_enforcement_allows_authorized():
    """Verify require_role allows authorized role."""
    sup_user = AuthenticatedUser(
        user_id="sup-1",
        email="supervisor@dispatchgrid.io",
        role=AppRole.SUPERVISOR,
    )
    supervisor_checker = require_role([AppRole.SUPERVISOR])
    authed = supervisor_checker(user=sup_user)
    assert authed.role == AppRole.SUPERVISOR

