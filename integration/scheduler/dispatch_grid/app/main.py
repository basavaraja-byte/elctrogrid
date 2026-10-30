"""DispatchGrid FastAPI entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes.dispatch import router as dispatch_router
from app.api.routes.recovery import router as recovery_router
from app.api.routes.scheduling import InMemoryScheduleRunStore, router as scheduling_router
from app.scheduler.dispatch import DispatchSessionStore
from app.scheduler.recovery import IdempotentRequestRegistry
from app.schemas.scheduling import ErrorResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def create_app() -> FastAPI:
    """Create and configure the DispatchGrid FastAPI application."""
    application = FastAPI(
        title="DispatchGrid — Workforce Scheduling & Optimization Engine",
        description=(
            "Modules B (Constraint-First Scheduling Engine) and C (Bounded Local-Search "
            "Assignment Optimization) for electrical field-service operations."
        ),
        version="1.0.0",
    )

    application.state.schedule_store = InMemoryScheduleRunStore()
    application.state.dispatch_store = DispatchSessionStore()
    application.state.idempotency_registry = IdempotentRequestRegistry()

    @application.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        payload = ErrorResponse(
            error_code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            details=[],
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @application.exception_handler(RequestValidationError)
    async def request_validation_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            f"{'.'.join(str(loc) for loc in err.get('loc', []))}: {err.get('msg', '')}"
            for err in exc.errors()
        ]
        payload = ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Invalid request payload.",
            details=details,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=payload.model_dump(),
        )

    @application.get("/health", tags=["system"])
    def health_check() -> dict[str, str]:
        return {"status": "ok", "service": "dispatchgrid-scheduler"}

    application.include_router(scheduling_router)
    application.include_router(dispatch_router)
    application.include_router(recovery_router)
    return application


app = create_app()

