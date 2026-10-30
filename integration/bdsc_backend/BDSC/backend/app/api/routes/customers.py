"""External Customer (Client) management API routes."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import CustomerType
from app.schemas.customer import (
    CustomerCreate,
    CustomerResponse,
    CustomerStatusPatch,
    CustomerUpdate,
)
from app.schemas.job import JobResponse
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
) -> CustomerResponse:
    """Create a new external Customer (Client) record with an auto-generated unique customer_code."""
    customer = CustomerService.create_customer(db, payload)
    return CustomerResponse.model_validate(customer)


@router.get(
    "",
    response_model=list[CustomerResponse],
)
def list_customers(
    customer_type: CustomerType | None = Query(default=None),
    city: str | None = Query(default=None),
    state: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[CustomerResponse]:
    """List external customers with optional filters."""
    customers = CustomerService.list_customers(
        db,
        customer_type=customer_type,
        city=city,
        state=state,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )
    return [CustomerResponse.model_validate(c) for c in customers]


@router.get(
    "/by-code/{customer_code}",
    response_model=CustomerResponse,
)
def get_customer_by_code(
    customer_code: str,
    db: Session = Depends(get_db),
) -> CustomerResponse:
    """Retrieve a single Customer by unique customer_code."""
    customer = CustomerService.get_customer_by_code(db, customer_code)
    return CustomerResponse.model_validate(customer)


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
)
def get_customer(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> CustomerResponse:
    """Retrieve a single Customer by UUID."""
    customer = CustomerService.get_customer_by_id(db, customer_id)
    return CustomerResponse.model_validate(customer)


@router.put(
    "/{customer_id}",
    response_model=CustomerResponse,
)
def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
) -> CustomerResponse:
    """Full update of an external Customer record."""
    customer = CustomerService.update_customer(db, customer_id, payload)
    return CustomerResponse.model_validate(customer)


@router.patch(
    "/{customer_id}/status",
    response_model=CustomerResponse,
)
def patch_customer_status(
    customer_id: uuid.UUID,
    payload: CustomerStatusPatch,
    db: Session = Depends(get_db),
) -> CustomerResponse:
    """Update a Customer's is_active status."""
    customer = CustomerService.patch_customer_status(db, customer_id, payload)
    return CustomerResponse.model_validate(customer)


@router.get(
    "/{customer_id}/jobs",
    response_model=list[JobResponse],
)
def list_customer_jobs(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[JobResponse]:
    """List all electrical service jobs requested by a specific Customer."""
    jobs = CustomerService.list_customer_jobs(db, customer_id)
    return [JobResponse.model_validate(j) for j in jobs]

