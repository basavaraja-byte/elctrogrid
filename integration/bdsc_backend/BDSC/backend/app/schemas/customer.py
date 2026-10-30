"""Pydantic v2 schemas for Customer (External Client) CRUD and validation."""

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import CustomerType
from app.utils.validators import validate_email_format, validate_phone_format

CUSTOMER_EXAMPLE = {
    "full_name": "Meera Reddy",
    "email": "facilities@apextechpark.in",
    "phone_number": "+91-80-40901122",
    "alternate_phone_number": "+91-9900112233",
    "customer_type": "BUSINESS",
    "company_name": "Apex Tech Park Pvt Ltd",
    "service_address": "Plot 14, EPIP Zone Phase 2, Whitefield",
    "city": "Bengaluru",
    "state": "Karnataka",
    "postal_code": "560066",
    "latitude": 12.9710,
    "longitude": 77.7510,
    "is_active": True,
}


class CustomerBase(BaseModel):
    """Shared properties for creating and updating an external Customer (Client)."""

    full_name: str = Field(..., min_length=2, max_length=200)
    email: str | None = Field(default=None, max_length=255)
    phone_number: str = Field(..., min_length=7, max_length=32)
    alternate_phone_number: str | None = Field(default=None, max_length=32)
    customer_type: CustomerType = Field(default=CustomerType.INDIVIDUAL)
    company_name: str | None = Field(default=None, max_length=255)
    service_address: str = Field(..., min_length=3, max_length=500)
    city: str = Field(..., min_length=2, max_length=120)
    state: str = Field(..., min_length=2, max_length=120)
    postal_code: str = Field(..., min_length=3, max_length=32)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    is_active: bool = Field(default=True)

    @field_validator("full_name", "service_address", "city", "state", "postal_code")
    @classmethod
    def validate_trimmed_required_string(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Field cannot be blank or whitespace only.")
        return trimmed

    @field_validator("company_name")
    @classmethod
    def validate_optional_company_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed if trimmed else None

    @field_validator("email")
    @classmethod
    def validate_optional_email(cls, v: str | None) -> str | None:
        return validate_email_format(v)

    @field_validator("phone_number")
    @classmethod
    def validate_required_phone(cls, v: str) -> str:
        cleaned = validate_phone_format(v, required=True)
        if not cleaned:
            raise ValueError("Phone number is required.")
        return cleaned

    @field_validator("alternate_phone_number")
    @classmethod
    def validate_optional_alternate_phone(cls, v: str | None) -> str | None:
        return validate_phone_format(v, required=False)


class CustomerCreate(CustomerBase):
    """Request schema for POST /api/v1/customers."""

    model_config = ConfigDict(json_schema_extra={"example": CUSTOMER_EXAMPLE})

    customer_code: str | None = Field(
        default=None,
        max_length=32,
        description="Optional unique customer code; automatically generated (e.g. CUST-A1B2C3D4) if omitted.",
    )

    @field_validator("customer_code")
    @classmethod
    def validate_optional_customer_code(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip().upper()
        return cleaned if cleaned else None


class CustomerUpdate(CustomerBase):
    """Request schema for PUT /api/v1/customers/{customer_id}."""

    model_config = ConfigDict(json_schema_extra={"example": CUSTOMER_EXAMPLE})


class CustomerStatusPatch(BaseModel):
    """Request schema for PATCH /api/v1/customers/{customer_id}/status."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_active": True,
                "reason": "Customer account verified and active",
            }
        }
    )

    is_active: bool
    reason: str = Field(default="Customer active status updated via API", max_length=500)


class CustomerResponse(BaseModel):
    """Response schema for Customer records."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_code: str
    full_name: str
    email: str | None = None
    phone_number: str
    alternate_phone_number: str | None = None
    customer_type: CustomerType
    company_name: str | None = None
    service_address: str
    city: str
    state: str
    postal_code: str
    latitude: float
    longitude: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
