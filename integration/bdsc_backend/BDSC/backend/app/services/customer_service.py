"""Customer (External Client) management service with unique code generation and validation."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.models.customer import Customer
from app.models.enums import CustomerType
from app.models.job import Job
from app.schemas.customer import CustomerCreate, CustomerStatusPatch, CustomerUpdate
from app.services.audit_service import AuditService
from app.utils.validators import (
    generate_customer_code,
    validate_coordinates,
    validate_email_format,
    validate_phone_format,
)


class CustomerService:
    """Service layer for external Customer (Client) CRUD and job history queries."""

    @staticmethod
    def _generate_unique_customer_code(db: Session, prefix: str = "CUST") -> str:
        """Generate a unique customer_code guaranteed not to collide with existing records."""
        for _ in range(10):
            candidate = generate_customer_code(prefix=prefix)
            existing = db.scalars(
                select(Customer).where(Customer.customer_code == candidate)
            ).first()
            if not existing:
                return candidate
        # Fallback with full UUID hex segment if needed
        return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"

    @classmethod
    def create_customer(cls, db: Session, payload: CustomerCreate) -> Customer:
        """Create and persist a new external Customer (Client) record."""
        validate_coordinates(payload.latitude, payload.longitude)
        cleaned_email = validate_email_format(payload.email)
        cleaned_phone = validate_phone_format(payload.phone_number)
        cleaned_alt_phone = validate_phone_format(payload.alternate_phone_number)

        if not cleaned_phone:
            raise ValidationException(
                code="VALIDATION_ERROR",
                message="Phone number is required for customer registration.",
                status_code=400,
            )

        if payload.customer_code:
            existing = db.scalars(
                select(Customer).where(Customer.customer_code == payload.customer_code)
            ).first()
            if existing:
                raise ConflictException(
                    code="DUPLICATE_CUSTOMER_CODE",
                    message=f"Customer with customer_code '{payload.customer_code}' already exists.",
                    details=[{"field": "customer_code", "value": payload.customer_code}],
                )
            unique_code = payload.customer_code
        else:
            unique_code = cls._generate_unique_customer_code(db)

        customer = Customer(
            customer_code=unique_code,
            full_name=payload.full_name,
            email=cleaned_email,
            phone_number=cleaned_phone,
            alternate_phone_number=cleaned_alt_phone,
            customer_type=payload.customer_type.value,
            company_name=payload.company_name,
            service_address=payload.service_address,
            city=payload.city,
            state=payload.state,
            postal_code=payload.postal_code,
            latitude=payload.latitude,
            longitude=payload.longitude,
            is_active=payload.is_active,
        )
        db.add(customer)
        db.flush()

        AuditService.log_event(
            db,
            entity_type="CUSTOMER",
            entity_id=customer.id,
            action="CREATE",
            new_value={
                "customer_code": customer.customer_code,
                "full_name": customer.full_name,
                "customer_type": customer.customer_type,
                "company_name": customer.company_name,
                "city": customer.city,
                "state": customer.state,
                "is_active": customer.is_active,
            },
            reason="Created external customer record",
        )
        db.commit()
        db.refresh(customer)
        return customer

    @staticmethod
    def get_customer_by_id(db: Session, customer_id: uuid.UUID) -> Customer:
        """Retrieve a Customer by UUID or raise 404 NotFoundException."""
        customer = db.get(Customer, customer_id)
        if not customer:
            raise NotFoundException("Customer", customer_id)
        return customer

    @staticmethod
    def get_customer_by_code(db: Session, customer_code: str) -> Customer:
        """Retrieve a Customer by unique customer_code or raise 404 NotFoundException."""
        stmt = select(Customer).where(Customer.customer_code == customer_code.strip().upper())
        customer = db.scalars(stmt).first()
        if not customer:
            raise NotFoundException("Customer", customer_code)
        return customer

    @staticmethod
    def list_customers(
        db: Session,
        *,
        customer_type: CustomerType | None = None,
        city: str | None = None,
        state: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Customer]:
        """List external customers with optional filtering."""
        stmt = select(Customer).order_by(Customer.created_at.desc(), Customer.full_name.asc())

        if customer_type is not None:
            stmt = stmt.where(Customer.customer_type == customer_type.value)
        if city is not None:
            stmt = stmt.where(Customer.city == city.strip())
        if state is not None:
            stmt = stmt.where(Customer.state == state.strip())
        if is_active is not None:
            stmt = stmt.where(Customer.is_active == is_active)

        customers = list(db.scalars(stmt).all())
        return customers[skip : skip + limit]

    @classmethod
    def update_customer(
        cls,
        db: Session,
        customer_id: uuid.UUID,
        payload: CustomerUpdate,
    ) -> Customer:
        """Update an existing Customer record while preserving its unique customer_code."""
        customer = cls.get_customer_by_id(db, customer_id)
        validate_coordinates(payload.latitude, payload.longitude)
        cleaned_email = validate_email_format(payload.email)
        cleaned_phone = validate_phone_format(payload.phone_number)
        cleaned_alt_phone = validate_phone_format(payload.alternate_phone_number)

        if not cleaned_phone:
            raise ValidationException(
                code="VALIDATION_ERROR",
                message="Phone number is required.",
                status_code=400,
            )

        old_snapshot = {
            "full_name": customer.full_name,
            "email": customer.email,
            "phone_number": customer.phone_number,
            "customer_type": customer.customer_type,
            "company_name": customer.company_name,
            "service_address": customer.service_address,
            "city": customer.city,
            "state": customer.state,
            "postal_code": customer.postal_code,
            "is_active": customer.is_active,
        }

        customer.full_name = payload.full_name
        customer.email = cleaned_email
        customer.phone_number = cleaned_phone
        customer.alternate_phone_number = cleaned_alt_phone
        customer.customer_type = payload.customer_type.value
        customer.company_name = payload.company_name
        customer.service_address = payload.service_address
        customer.city = payload.city
        customer.state = payload.state
        customer.postal_code = payload.postal_code
        customer.latitude = payload.latitude
        customer.longitude = payload.longitude
        customer.is_active = payload.is_active

        new_snapshot = {
            "full_name": customer.full_name,
            "email": customer.email,
            "phone_number": customer.phone_number,
            "customer_type": customer.customer_type,
            "company_name": customer.company_name,
            "service_address": customer.service_address,
            "city": customer.city,
            "state": customer.state,
            "postal_code": customer.postal_code,
            "is_active": customer.is_active,
        }

        AuditService.log_event(
            db,
            entity_type="CUSTOMER",
            entity_id=customer.id,
            action="UPDATE",
            old_value=old_snapshot,
            new_value=new_snapshot,
            reason="Updated customer details",
        )
        db.commit()
        db.refresh(customer)
        return customer

    @classmethod
    def patch_customer_status(
        cls,
        db: Session,
        customer_id: uuid.UUID,
        payload: CustomerStatusPatch,
    ) -> Customer:
        """Toggle a Customer's is_active status."""
        customer = cls.get_customer_by_id(db, customer_id)
        old_status = customer.is_active
        customer.is_active = payload.is_active

        AuditService.log_event(
            db,
            entity_type="CUSTOMER",
            entity_id=customer.id,
            action="STATUS_CHANGE",
            old_value={"is_active": old_status},
            new_value={"is_active": customer.is_active},
            reason=payload.reason,
        )
        db.commit()
        db.refresh(customer)
        return customer

    @classmethod
    def list_customer_jobs(cls, db: Session, customer_id: uuid.UUID) -> list[Job]:
        """List all service jobs associated with a specific Customer."""
        cls.get_customer_by_id(db, customer_id)
        stmt = (
            select(Job)
            .where(Job.customer_id == customer_id)
            .order_by(Job.appointment_window_start.desc())
        )
        return list(db.scalars(stmt).all())

