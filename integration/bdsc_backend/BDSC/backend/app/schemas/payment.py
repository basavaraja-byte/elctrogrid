from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PaymentConfigResponse(BaseModel):
    payment_mode: str
    razorpay_configured: bool
    razorpay_key_id: str | None = None
    demo_payment_enabled: bool
    currency: str = "INR"


class CreatePaymentOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    booking_code: str = Field(..., min_length=3, max_length=50)
    amount_inr: float | None = Field(default=1120.0, ge=1.0)


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
    model_config = ConfigDict(extra="forbid")

    booking_code: str = Field(..., min_length=3, max_length=50)
    razorpay_order_id: str = Field(..., min_length=4, max_length=100)
    razorpay_payment_id: str = Field(..., min_length=4, max_length=100)
    razorpay_signature: str = Field(..., min_length=8, max_length=256)


class RecordPaymentFailureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    booking_code: str = Field(..., min_length=3, max_length=50)
    razorpay_order_id: str | None = Field(default=None, max_length=100)
    reason: str = Field(..., min_length=2, max_length=500)


class DemoSimulatePaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    booking_code: str = Field(..., min_length=3, max_length=50)
    outcome: str = Field(default="DEMO_SIMULATED", description="DEMO_SIMULATED | FAILED")
    acknowledge_simulation: bool = Field(
        default=True,
        description="Must be true to confirm awareness that this is an unverified demo simulation.",
    )


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
    message: str

