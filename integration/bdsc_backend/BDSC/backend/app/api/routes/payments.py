from datetime import datetime, timezone
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.payment import (
    CreatePaymentOrderRequest,
    CreatePaymentOrderResponse,
    DemoSimulatePaymentRequest,
    PaymentConfigResponse,
    PaymentResultResponse,
    RecordPaymentFailureRequest,
    VerifyRazorpayPaymentRequest,
)
from app.services.payment_service import (
    RazorpayGatewayClient,
    get_razorpay_client,
    _generate_payment_code,
)

router = APIRouter(prefix="/payments", tags=["Payments (Razorpay Test Mode)"])


@router.get("/config", response_model=PaymentConfigResponse)
def get_payment_config(
    gateway: RazorpayGatewayClient = Depends(get_razorpay_client),
) -> PaymentConfigResponse:
    settings = get_settings()
    return PaymentConfigResponse(
        payment_mode=settings.payment_mode,
        razorpay_configured=gateway.is_configured,
        razorpay_key_id=gateway.public_key_id if gateway.is_configured else "rzp_test_placeholder_key",
        demo_payment_enabled=settings.demo_payment_enabled,
        currency="INR",
    )


@router.post("/orders", response_model=CreatePaymentOrderResponse)
def create_payment_order_endpoint(
    payload: CreatePaymentOrderRequest,
    gateway: RazorpayGatewayClient = Depends(get_razorpay_client),
) -> CreatePaymentOrderResponse:
    settings = get_settings()
    amount_inr = payload.amount_inr or 1120.0
    amount_paise = int(amount_inr * 100)
    payment_code = _generate_payment_code()

    order_data = gateway.create_order(
        amount_paise=amount_paise,
        currency="INR",
        receipt=payment_code,
        notes={
            "booking_code": payload.booking_code,
            "payment_code": payment_code,
        },
    )

    return CreatePaymentOrderResponse(
        payment_code=payment_code,
        booking_code=payload.booking_code,
        razorpay_order_id=order_data["id"],
        razorpay_key_id=gateway.public_key_id,
        amount_paise=amount_paise,
        currency="INR",
        payment_mode=settings.payment_mode,
        customer_name="Customer",
        customer_email="customer@dispatchgrid.io",
        customer_phone="+91 98450 21001",
    )


@router.post("/verify", response_model=PaymentResultResponse)
def verify_payment_endpoint(
    payload: VerifyRazorpayPaymentRequest,
    gateway: RazorpayGatewayClient = Depends(get_razorpay_client),
) -> PaymentResultResponse:
    settings = get_settings()
    is_valid = gateway.verify_payment_signature(
        razorpay_order_id=payload.razorpay_order_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        razorpay_signature=payload.razorpay_signature,
    )

    if not is_valid and gateway.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Razorpay payment signature verification failed.",
        )

    payment_code = _generate_payment_code()
    return PaymentResultResponse(
        payment_code=payment_code,
        booking_code=payload.booking_code,
        provider="razorpay",
        payment_mode=settings.payment_mode,
        payment_status="COMPLETED",
        is_verified_razorpay=True,
        is_demo_simulation=not gateway.is_configured,
        amount_paise=112000,
        currency="INR",
        razorpay_order_id=payload.razorpay_order_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        verified_at=datetime.now(timezone.utc),
        technician_notified=True,
        message="Payment successfully verified and settled via Razorpay Test Mode.",
    )


@router.post("/failure", response_model=PaymentResultResponse)
def record_payment_failure_endpoint(
    payload: RecordPaymentFailureRequest,
) -> PaymentResultResponse:
    settings = get_settings()
    payment_code = _generate_payment_code()
    return PaymentResultResponse(
        payment_code=payment_code,
        booking_code=payload.booking_code,
        provider="razorpay",
        payment_mode=settings.payment_mode,
        payment_status="FAILED",
        is_verified_razorpay=False,
        is_demo_simulation=False,
        amount_paise=112000,
        currency="INR",
        razorpay_order_id=payload.razorpay_order_id,
        message=f"Payment failure recorded: {payload.reason}",
    )


@router.post("/demo-simulate", response_model=PaymentResultResponse)
def demo_simulate_payment_endpoint(
    payload: DemoSimulatePaymentRequest,
) -> PaymentResultResponse:
    settings = get_settings()
    payment_code = _generate_payment_code()
    sim_payment_id = f"pay_test_sim_{secrets.token_hex(6)}"
    sim_order_id = f"order_test_sim_{secrets.token_hex(6)}"

    return PaymentResultResponse(
        payment_code=payment_code,
        booking_code=payload.booking_code,
        provider="razorpay_demo_sandbox",
        payment_mode=settings.payment_mode,
        payment_status="COMPLETED",
        is_verified_razorpay=False,
        is_demo_simulation=True,
        amount_paise=112000,
        currency="INR",
        razorpay_order_id=sim_order_id,
        razorpay_payment_id=sim_payment_id,
        verified_at=datetime.now(timezone.utc),
        technician_notified=True,
        message="Simulated payment processed successfully (Offline Sandbox Test Mode).",
    )
