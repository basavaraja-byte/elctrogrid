"""Pydantic schemas for Payment, Billing, Damaged Components, Invoices & Razorpay."""

from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field


class PaymentConfigResponse(BaseModel):
    payment_mode: str
    razorpay_configured: bool
    razorpay_key_id: str | None = None
    demo_payment_enabled: bool
    currency: str = "INR"


class DamagedComponentItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    component_name: str = Field(..., min_length=1, max_length=255)
    damage_description: str = Field(..., min_length=1, max_length=1000)
    quantity: int = Field(default=1, ge=1)
    photo_url: str | None = None
    price_status: str = Field(default="Price to be confirmed")
    estimated_part_amount_paise: int | None = None
    remarks: str | None = None


class DamagedComponentResponse(DamagedComponentItem):
    id: str
    job_id: str
    reported_by: str | None = None
    created_at: datetime


class BillingCalculation(BaseModel):
    """Accurate server-calculated time-based billing breakdown."""
    duration_minutes: int
    duration_formatted: str
    base_amount_inr: int = 500
    base_amount_paise: int = 50000
    additional_blocks: int
    additional_amount_inr: int
    additional_amount_paise: int
    labour_total_inr: int
    labour_total_paise: int
    currency: str = "INR"


class JobCompleteBillingRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    work_summary: str = Field(..., min_length=3, max_length=2000)
    damaged_components: list[DamagedComponentItem] = Field(default_factory=list)
    materials_used: list[str] = Field(default_factory=list)
    notes: str | None = None


class CashPaymentInitiateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    job_id: str


class CashPaymentConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    job_id: str
    confirmed_by_name: str
    confirmed_by_role: str = "technician"  # technician or supervisor


class CreatePaymentOrderRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    booking_code: str = Field(..., min_length=1, max_length=50)
    amount_inr: float | None = Field(default=None, ge=1.0)


class CreatePaymentOrderResponse(BaseModel):
    payment_code: str
    booking_code: str
    razorpay_order_id: str
    razorpay_key_id: str
    amount_paise: int
    currency: str
    payment_mode: str
    customer_name: str
    customer_email: str
    customer_phone: str


class VerifyRazorpayPaymentRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    booking_code: str = Field(..., min_length=1, max_length=50)
    razorpay_order_id: str = Field(..., min_length=4, max_length=100)
    razorpay_payment_id: str = Field(..., min_length=4, max_length=100)
    razorpay_signature: str = Field(..., min_length=8, max_length=256)


class RecordPaymentFailureRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    booking_code: str = Field(..., min_length=1, max_length=50)
    razorpay_order_id: str | None = Field(default=None, max_length=100)
    reason: str = Field(..., min_length=2, max_length=500)


class DemoSimulatePaymentRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    booking_code: str = Field(..., min_length=1, max_length=50)
    outcome: str = Field(default="DEMO_SIMULATED")
    acknowledge_simulation: bool = Field(default=True)


class InvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    payment_id: str
    job_id: str
    customer_id: str | None = None
    technician_id: str | None = None
    customer_name: str
    technician_name: str
    service_description: str
    invoice_date: datetime
    duration_minutes: int
    duration_formatted: str
    labour_amount_inr: int
    additional_amount_inr: int
    parts_status: str = "Price to be confirmed"
    parts_amount_inr: int | None = None
    total_paid_inr: int
    total_paid_paise: int
    payment_method: str
    payment_status: str
    payment_reference: str
    pdf_url: str | None = None
    damaged_components: list[DamagedComponentItem] = Field(default_factory=list)


class JobPaymentDetailsResponse(BaseModel):
    payment_id: str
    payment_reference: str
    job_id: str
    job_reference: str
    customer_id: str | None = None
    customer_name: str
    technician_id: str | None = None
    technician_name: str
    work_started_at: datetime
    work_completed_at: datetime
    duration_minutes: int
    duration_formatted: str
    base_amount_inr: int
    base_amount_paise: int
    additional_blocks: int
    additional_amount_inr: int
    additional_amount_paise: int
    labour_total_inr: int
    labour_total_paise: int
    currency: str = "INR"
    payment_method: str
    payment_status: str  # PENDING, PAID, FAILED
    damaged_components: list[DamagedComponentItem] = Field(default_factory=list)
    invoice_number: str | None = None
    invoice: InvoiceResponse | None = None
    is_verified: bool = False
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None


class PaymentResultResponse(BaseModel):
    payment_code: str
    booking_code: str
    provider: str
    payment_mode: str
    payment_status: str
    is_verified_razorpay: bool
    is_demo_simulation: bool
    amount_paise: int
    currency: str
    razorpay_order_id: str | None = None
    razorpay_payment_id: str | None = None
    verified_at: datetime | None = None
    technician_notified: bool = False
    invoice_number: str | None = None
    message: str


class SupervisorPaymentSummaryResponse(BaseModel):
    total_due_inr: int
    total_received_inr: int
    pending_cash_count: int
    successful_upi_count: int
    successful_cash_count: int
    failed_attempts_count: int
    total_service_revenue_inr: int
    payments: list[JobPaymentDetailsResponse] = Field(default_factory=list)
