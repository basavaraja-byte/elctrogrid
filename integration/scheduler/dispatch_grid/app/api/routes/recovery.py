"""FastAPI routes for D01-D07 Disruption Recovery, Simulation, and Idempotent Job Submission."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from app.api.routes.scheduling import (
    ScheduleRunRepository,
    StoredScheduleRecord,
    get_schedule_store,
)
from app.scheduler.dataset_loader import load_dataset_bundle
from app.scheduler.recovery import (
    IdempotencyConflictError,
    IdempotentRequestRegistry,
    RecoveryError,
    advance_commitments_to_event_time,
    get_scenario_specifications,
    simulate_all_scenarios,
    simulate_scenario,
    submit_idempotent_job,
)
from app.schemas.dispatch_recovery import (
    IdempotentJobSubmissionRequest,
    IdempotentJobSubmissionResponse,
    ScenarioRecoveryResult,
    ScenarioSpecification,
    SimulateAllScenariosRequest,
    SimulateAllScenariosResponse,
    SimulateScenarioRequest,
)


def get_idempotency_registry(request: Request) -> IdempotentRequestRegistry:
    """FastAPI dependency retrieving the active IdempotentRequestRegistry from app.state."""
    registry = getattr(request.app.state, "idempotency_registry", None)
    if registry is None:
        registry = IdempotentRequestRegistry()
        request.app.state.idempotency_registry = registry
    return registry


router = APIRouter(prefix="/api/v1/scheduling/recovery", tags=["recovery"])


def _translate_recovery_error(exc: RecoveryError) -> HTTPException:
    if isinstance(exc, IdempotencyConflictError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"[{exc.error_code}] {exc.message}",
        )
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"[{exc.error_code}] {exc.message}",
    )


@router.get(
    "/scenarios",
    response_model=dict[str, ScenarioSpecification],
    summary="List formal disruption specifications (D01-D07): triggers, targets, constraints, and outcomes",
)
def list_disruption_scenarios() -> dict[str, ScenarioSpecification]:
    return get_scenario_specifications()


@router.post(
    "/simulate",
    response_model=ScenarioRecoveryResult,
    summary="Simulate a single disruption scenario (D01-D07) with protected-assignment and idempotency guarantees",
)
def run_scenario_simulation(
    payload: SimulateScenarioRequest,
    schedule_store: ScheduleRunRepository = Depends(get_schedule_store),
    idempotency_registry: IdempotentRequestRegistry = Depends(get_idempotency_registry),
) -> ScenarioRecoveryResult:
    baseline_result = None
    if payload.baseline_run_id is not None:
        stored = schedule_store.get(payload.baseline_run_id)
        if stored is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Baseline schedule run '{payload.baseline_run_id}' not found.",
            )
        baseline_result = stored.result

    try:
        result = simulate_scenario(
            scenario_id=payload.scenario_id,
            baseline_result=baseline_result,
            config=payload.config,
            locked_future_job_ids=payload.locked_future_job_ids,
            existing_assignments_override=payload.existing_assignments_override,
            idempotency_key=payload.idempotency_key,
            idempotency_registry=idempotency_registry,
        )
    except RecoveryError as exc:
        raise _translate_recovery_error(exc) from exc

    if not result.idempotent_replay:
        scen_bundle = load_dataset_bundle(scenario_ids=[payload.scenario_id])
        sc_obj = next(s for s in scen_bundle.scenarios if s.scenario_id == payload.scenario_id)
        existing_used = (
            payload.existing_assignments_override
            if payload.existing_assignments_override is not None
            else (
                advance_commitments_to_event_time(
                    baseline_assignments=baseline_result.final_schedule.assignments,
                    event_time_min=sc_obj.event_time_min,
                    scenario=sc_obj,
                    config=payload.config,
                    locked_future_job_ids=set(payload.locked_future_job_ids),
                )
                if baseline_result is not None
                else []
            )
        )
        schedule_store.save(
            StoredScheduleRecord(
                result=result.recovered_schedule_run,
                jobs=scen_bundle.jobs,
                electricians=scen_bundle.electricians,
                travel_times=scen_bundle.travel_entries,
                unavailability=scen_bundle.unavailability,
                existing_assignments=existing_used,
            )
        )

    return result


@router.post(
    "/simulate-all",
    response_model=SimulateAllScenariosResponse,
    summary="Execute the full reproducible D01-D07 disruption recovery simulation suite",
)
def run_all_scenario_simulations(
    payload: SimulateAllScenariosRequest = Body(default_factory=SimulateAllScenariosRequest),
) -> SimulateAllScenariosResponse:
    try:
        return simulate_all_scenarios(
            scenario_ids=payload.scenario_ids,
            config=payload.config,
        )
    except RecoveryError as exc:
        raise _translate_recovery_error(exc) from exc


@router.post(
    "/jobs/idempotent",
    response_model=IdempotentJobSubmissionResponse,
    summary="Submit a job request with idempotency-key deduplication (D06 protection)",
)
def submit_job_idempotently(
    payload: IdempotentJobSubmissionRequest,
    schedule_store: ScheduleRunRepository = Depends(get_schedule_store),
    idempotency_registry: IdempotentRequestRegistry = Depends(get_idempotency_registry),
) -> IdempotentJobSubmissionResponse:
    baseline_result = None
    if payload.baseline_run_id is not None:
        stored = schedule_store.get(payload.baseline_run_id)
        if stored is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Baseline schedule run '{payload.baseline_run_id}' not found.",
            )
        baseline_result = stored.result

    try:
        resp = submit_idempotent_job(
            idempotency_key=payload.idempotency_key,
            job=payload.job,
            registry=idempotency_registry,
            baseline_result=baseline_result,
            event_time_min=payload.event_time_min,
            reschedule_immediately=payload.reschedule_immediately,
            config=payload.config,
        )
    except RecoveryError as exc:
        raise _translate_recovery_error(exc) from exc

    if resp.created and resp.schedule_run is not None:
        bundle = load_dataset_bundle()
        merged_jobs = list(bundle.jobs)
        if all(j.job_id != payload.job.job_id for j in merged_jobs):
            merged_jobs.append(payload.job)
        schedule_store.save(
            StoredScheduleRecord(
                result=resp.schedule_run,
                jobs=merged_jobs,
                electricians=bundle.electricians,
                travel_times=bundle.travel_entries,
                unavailability=bundle.unavailability,
                existing_assignments=[],
            )
        )

    return resp

