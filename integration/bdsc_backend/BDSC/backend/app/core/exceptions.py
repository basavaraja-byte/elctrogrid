"""Unified application exceptions and FastAPI error handlers."""

from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


class AppException(Exception):
    """Base application exception with canonical error code, message, and details."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []


class NotFoundException(AppException):
    """Raised when a requested entity is not found (404)."""

    def __init__(self, entity: str, entity_id: Any) -> None:
        super().__init__(
            code="NOT_FOUND",
            message=f"{entity} with id '{entity_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            details=[{"entity": entity, "id": str(entity_id)}],
        )


class ConflictException(AppException):
    """Raised on resource conflict, overlap, or duplicate idempotency key (409)."""

    def __init__(
        self,
        message: str,
        code: str = "CONFLICT",
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details or [],
        )


class ValidationException(AppException):
    """Raised on domain validation or business rule violation (400 or 422)."""

    def __init__(
        self,
        message: str,
        code: str = "VALIDATION_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status_code,
            details=details or [],
        )


def build_error_payload(
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Construct the canonical error response envelope."""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        },
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Attach canonical exception handlers to the FastAPI application."""

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(
                code=exc.code,
                message=exc.message,
                details=exc.details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        formatted_details: list[dict[str, Any]] = []
        for err in exc.errors():
            loc_parts = [str(part) for part in err.get("loc", []) if part != "body"]
            field_name = ".".join(loc_parts) if loc_parts else "request"
            formatted_details.append(
                {
                    "field": field_name,
                    "issue": err.get("msg", "Invalid value"),
                    "type": err.get("type", "value_error"),
                }
            )
        return JSONResponse(
            status_code=422,
            content=build_error_payload(
                code="VALIDATION_ERROR",
                message="Request payload validation failed.",
                details=formatted_details,
            ),
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        # Handle database unique, foreign-key, and check constraint violations cleanly
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=build_error_payload(
                code="DATABASE_CONSTRAINT_VIOLATION",
                message="Database integrity or constraint violation occurred.",
                details=[{"issue": "Unique, foreign-key, or check constraint violated."}],
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_sqlalchemy_error(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        # Never expose database credentials or internal SQL stack traces
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=build_error_payload(
                code="DATABASE_ERROR",
                message="A database operation failed. Transaction has been rolled back.",
                details=[],
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Never expose internal stack traces to API consumers
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=build_error_payload(
                code="INTERNAL_ERROR",
                message="An unexpected internal server error occurred.",
                details=[],
            ),
        )
