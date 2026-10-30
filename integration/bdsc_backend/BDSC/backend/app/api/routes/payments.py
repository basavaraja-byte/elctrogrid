"""Comprehensive Payments, Time-Based Billing, and Invoicing API Routes."""

from datetime import datetime, timezone
from pathlib import Path
import secrets
from typing import Any
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.payment import Invoice, Payment
from app.schemas.payment import (
    CashPaymentConfirmRequest,
    CashPaymentInitiateRequest,
    CreatePaymentOrderRequest,
    CreatePaymentOrderResponse,
    DemoSimulatePaymentRequest,
    InvoiceResponse,
    JobCompleteBillingRequest,
    JobPaymentDetailsResponse,
    PaymentConfigResponse,
    PaymentResultResponse,
    RecordPaymentFailureRequest,
    SupervisorPaymentSummaryResponse,
    VerifyRazorpayPaymentRequest,
)
from app.services.payment_service import (
    PaymentService,
    RazorpayGatewayClient,
    get_razorpay_client,
    _generate_payment_code,
)
from app.services.pdf_service import generate_invoice_pdf

router = APIRouter(prefix="/payments", tags=["Payments & Time-Based Billing"])


@router.get("/config", response_model=PaymentConfigResponse)
def get_payment_config(
    gateway: RazorpayGatewayClient = Depends(get_razorpay_client),
) -> PaymentConfigResponse:
    """Return Razorpay configuration for test mode checkout."""
    settings = get_settings()
    return PaymentConfigResponse(
        payment_mode=settings.payment_mode,
        razorpay_configured=gateway.is_configured,
        razorpay_key_id=gateway.public_key_id if gateway.is_configured else "rzp_test_placeholder_key",
        demo_payment_enabled=settings.demo_payment_enabled,
        currency="INR",
    )


@router.post("/jobs/{job_id}/start")
def start_job_endpoint(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Module 2: Technician starts job. Backend records actual_start_time with server timestamp."""
    job = PaymentService.record_job_start(db, job_id)
    return {
        "job_id": str(job.id),
        "status": job.status,
        "actual_start_time": job.actual_start_time.isoformat() if job.actual_start_time else None,
        "message": "Job work timer started successfully.",
    }


@router.post("/jobs/{job_id}/complete", response_model=JobPaymentDetailsResponse)
def complete_job_and_bill_endpoint(
    job_id: uuid.UUID,
    payload: JobCompleteBillingRequest,
    technician_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> JobPaymentDetailsResponse:
    """Modules 1, 2, 3, 4: Complete job, calculate duration and time-based bill,
    save damaged parts with 'Price to be confirmed', and create PENDING payment request.
    """
    PaymentService.complete_job_and_generate_bill(
        db, job_id, payload, technician_name=technician_name
    )
    return PaymentService.get_job_payment_details(db, job_id)


@router.get("/jobs/{job_id}", response_model=JobPaymentDetailsResponse)
def get_job_payment_endpoint(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> JobPaymentDetailsResponse:
    """Module 4, 10, 11: Retrieve payment request, itemized time slabs, damaged components, and receipt."""
    return PaymentService.get_job_payment_details(db, job_id)


@router.post("/jobs/{job_id}/cash/initiate")
def initiate_cash_payment_endpoint(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Module 5: Customer selects CASH. Displays exact labour amount payable.
    Payment remains PENDING until authenticated technician confirms.
    """
    details = PaymentService.get_job_payment_details(db, job_id)
    return {
        "job_id": str(job_id),
        "payment_method": "CASH",
        "payment_status": "PENDING",
        "amount_due_inr": details.labour_total_inr,
        "instructions": (
            f"Please pay ₹{details.labour_total_inr} in cash directly to your field technician. "
            "The technician will authenticate the receipt of cash on their terminal to instantly close the ticket and issue your official receipt."
        ),
    }


@router.post("/jobs/{job_id}/cash/confirm", response_model=JobPaymentDetailsResponse)
def confirm_cash_payment_endpoint(
    job_id: uuid.UUID,
    payload: CashPaymentConfirmRequest,
    db: Session = Depends(get_db),
) -> JobPaymentDetailsResponse:
    """Module 5 & 8: Authorized technician or supervisor confirms cash received.
    Updates status to PAID, generates official receipt, and closes job.
    """
    PaymentService.confirm_cash_payment(
        db,
        job_id,
        confirmed_by=payload.confirmed_by_name,
        confirmed_by_role=payload.confirmed_by_role,
    )
    return PaymentService.get_job_payment_details(db, job_id)


@router.post("/orders", response_model=CreatePaymentOrderResponse)
def create_payment_order_endpoint(
    payload: CreatePaymentOrderRequest,
    db: Session = Depends(get_db),
    gateway: RazorpayGatewayClient = Depends(get_razorpay_client),
) -> CreatePaymentOrderResponse:
    """Module 6: Create Razorpay UPI test order matching the calculated labour bill."""
    settings = get_settings()

    # Look up calculated amount from payment record if booking_code is a job UUID
    amount_inr = payload.amount_inr
    if not amount_inr:
        try:
            job_uuid = uuid.UUID(payload.booking_code)
            pmt = db.query(Payment).filter(Payment.job_id == job_uuid).first()
            if pmt:
                amount_inr = pmt.labour_total_paise / 100.0
        except ValueError:
            pass
    if not amount_inr:
        amount_inr = 500.0

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
    db: Session = Depends(get_db),
    gateway: RazorpayGatewayClient = Depends(get_razorpay_client),
) -> PaymentResultResponse:
    """Module 6 & 8: Verify Razorpay HMAC signature, settle payment as PAID, and generate receipt."""
    settings = get_settings()
    payment, invoice = PaymentService.verify_razorpay_and_settle(
        db,
        booking_code=payload.booking_code,
        razorpay_order_id=payload.razorpay_order_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        razorpay_signature=payload.razorpay_signature,
        gateway=gateway,
    )

    return PaymentResultResponse(
        payment_code=payment.payment_reference,
        booking_code=payload.booking_code,
        provider="razorpay",
        payment_mode=settings.payment_mode,
        payment_status="COMPLETED",
        is_verified_razorpay=True,
        is_demo_simulation=not gateway.is_configured,
        amount_paise=payment.labour_total_paise,
        currency="INR",
        razorpay_order_id=payload.razorpay_order_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        verified_at=payment.confirmed_at,
        technician_notified=True,
        invoice_number=invoice.invoice_number,
        message="Payment successfully verified and settled. Official receipt generated.",
    )


@router.post("/failure", response_model=PaymentResultResponse)
def record_payment_failure_endpoint(
    payload: RecordPaymentFailureRequest,
) -> PaymentResultResponse:
    """Record payment failure without corrupting job or technician workflow."""
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
        amount_paise=50000,
        currency="INR",
        razorpay_order_id=payload.razorpay_order_id,
        message=f"Payment failure recorded: {payload.reason}",
    )


@router.post("/demo-simulate", response_model=PaymentResultResponse)
def demo_simulate_payment_endpoint(
    payload: DemoSimulatePaymentRequest,
    db: Session = Depends(get_db),
) -> PaymentResultResponse:
    """Sandbox simulation for local presentation."""
    settings = get_settings()
    sim_order_id = f"order_test_sim_{secrets.token_hex(6)}"
    sim_payment_id = f"pay_test_sim_{secrets.token_hex(6)}"

    payment = None
    try:
        job_uuid = uuid.UUID(payload.booking_code)
        payment = db.query(Payment).filter(Payment.job_id == job_uuid).first()
    except ValueError:
        pass

    if payment:
        payment, invoice = PaymentService.confirm_cash_payment(
            db, payment.job_id, confirmed_by="Demo Gateway Simulation", confirmed_by_role="supervisor"
        )
        return PaymentResultResponse(
            payment_code=payment.payment_reference,
            booking_code=payload.booking_code,
            provider="razorpay_demo_sandbox",
            payment_mode=settings.payment_mode,
            payment_status="COMPLETED",
            is_verified_razorpay=False,
            is_demo_simulation=True,
            amount_paise=payment.labour_total_paise,
            currency="INR",
            razorpay_order_id=sim_order_id,
            razorpay_payment_id=sim_payment_id,
            verified_at=payment.confirmed_at,
            technician_notified=True,
            invoice_number=invoice.invoice_number,
            message="Simulated payment processed successfully (Offline Sandbox Test Mode).",
        )

    return PaymentResultResponse(
        payment_code=_generate_payment_code(),
        booking_code=payload.booking_code,
        provider="razorpay_demo_sandbox",
        payment_mode=settings.payment_mode,
        payment_status="COMPLETED",
        is_verified_razorpay=False,
        is_demo_simulation=True,
        amount_paise=50000,
        currency="INR",
        razorpay_order_id=sim_order_id,
        razorpay_payment_id=sim_payment_id,
        verified_at=datetime.now(timezone.utc),
        technician_notified=True,
        message="Simulated payment processed successfully.",
    )


@router.get("/invoices/{invoice_number}/pdf")
def download_invoice_pdf_endpoint(
    invoice_number: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Module 8: Download official service payment receipt PDF."""
    invoice = db.query(Invoice).filter(Invoice.invoice_number == invoice_number).first()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice not found: {invoice_number}")

    pdf_path = Path("static/invoices") / f"{invoice_number}.pdf"
    if not pdf_path.exists():
        job_hex = invoice.job_id.hex[:8].upper() if hasattr(invoice.job_id, 'hex') else str(invoice.job_id)[:8].upper()
        generate_invoice_pdf(
            invoice_number=invoice.invoice_number,
            invoice_date=invoice.invoice_date,
            customer_name=invoice.customer_name,
            job_reference=f"JOB-{job_hex}",
            technician_name=invoice.technician_name,
            service_description=invoice.service_description,
            duration_minutes=invoice.duration_minutes,
            base_amount_inr=invoice.labour_amount_paise // 100,
            additional_blocks=invoice.additional_amount_paise // 10000,
            additional_amount_inr=invoice.additional_amount_paise // 100,
            labour_total_inr=invoice.total_paid_paise // 100,
            payment_method=invoice.payment_method,
            payment_status=invoice.payment_status,
            payment_reference=invoice.invoice_number,
        )

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF receipt could not be generated.")

    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename=f"Receipt_{invoice_number}.pdf",
    )


@router.get("/summary", response_model=SupervisorPaymentSummaryResponse)
def get_supervisor_summary_endpoint(
    db: Session = Depends(get_db),
) -> SupervisorPaymentSummaryResponse:
    """Module 12: Supervisor payment monitoring & revenue analytics."""
    return PaymentService.get_supervisor_payment_summary(db)
