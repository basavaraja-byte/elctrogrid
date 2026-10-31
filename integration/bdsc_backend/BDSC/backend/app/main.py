"""FastAPI application entrypoint for DISPATCHGRID (Integrated Monolith)."""

from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routes import customers, dispatch, health, jobs, payments, recovery, schedules, scheduling, technicians
from app.ai.api.routes import router as ai_router
from app.api.routes.scheduling import InMemoryScheduleRunStore
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.scheduler.dispatch import DispatchSessionStore
from app.scheduler.recovery import IdempotentRequestRegistry
from app.services.schedule_service import ScheduleService
from app.services.scheduler_adapter import SchedulerEngineAdapter


def create_app() -> FastAPI:
    """Create and configure the unified DISPATCHGRID FastAPI application instance."""
    app = FastAPI(
        title=f"{settings.app_name} — Workforce Scheduling & Recovery Engine API",
        version="1.0.0",
        description=(
            "Integrated enterprise platform for DISPATCHGRID combining Electrical Field Service "
            "Management, Centralized Hard-Constraint Validation, Schedule Versioning & Approval, "
            "Greedy Baseline + Bounded Local Search Optimization, 5-Minute Technician Dispatch Timeout, "
            "and Reproducible Disruption Recovery Simulation (D01–D07)."
        ),
    )

    # State stores required by scheduler, dispatch timeout, and recovery engines
    app.state.schedule_store = InMemoryScheduleRunStore()
    app.state.dispatch_store = DispatchSessionStore()
    app.state.idempotency_registry = IdempotentRequestRegistry()

    # Register the Module B/C scheduling and optimization solver into ScheduleService
    ScheduleService.register_scheduler_engine(SchedulerEngineAdapter())

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    @app.get("/", include_in_schema=False)
    def root_redirect() -> RedirectResponse:
        """Redirect root URL to interactive Swagger UI documentation."""
        return RedirectResponse(url="/docs")

    @app.get("/health", tags=["Health"])
    @app.get("/healthz", tags=["Health"], include_in_schema=False)
    def root_health() -> dict:
        """Root-level health check endpoint for cloud platforms (Render, Vercel, K8s)."""
        return {
            "status": "healthy",
            "service": settings.app_name,
            "environment": settings.app_env,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    prefix = settings.api_v1_prefix
    # 1. Core Field Service Management & Persistence Routes
    app.include_router(health.router, prefix=prefix)
    app.include_router(customers.router, prefix=prefix)
    app.include_router(jobs.router, prefix=prefix)
    app.include_router(technicians.router, prefix=prefix)
    app.include_router(schedules.router, prefix=prefix)
    app.include_router(payments.router, prefix=prefix)

    # 2. Scheduling, Local-Search Optimization, 5-Minute Dispatch, and Recovery Simulation Routes
    app.include_router(scheduling.router)
    app.include_router(dispatch.router)
    app.include_router(recovery.router)

    # 3. AI & Machine Learning Predictive Services
    app.include_router(ai_router)

    return app


app = create_app()
