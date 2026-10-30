"""FastAPI scheduling routes and injectable persistence adapter contract (Section 13).

Integration points for teammates:
- Persistence team (Module A): Implement `ScheduleRunRepository` and bind it to
  `app.state.schedule_store` or override `get_schedule_store` via FastAPI `dependency_overrides`.
- Disruption Recovery team (Module D): Invoke `generate_schedule(...)` directly or call
  `POST /api/v1/scheduling/generate` / `POST /api/v1/scheduling/optimize` passing
  `existing_assignments` with protected statuses ('completed', 'in_progress', or locked=True).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.scheduler.dataset_loader import generate_dataset_audit, load_dataset_bundle
from app.scheduler.engine import generate_schedule
from app.schemas.scheduling import (
    DatasetAuditReport,
    Electrician,
    ExistingAssignment,
    GenerateScheduleRequest,
    Job,
    OptimizeScheduleRequest,
    ScheduleExplanationsResponse,
    ScheduleMetricsResponse,
    ScheduleRunResult,
    SchedulerConfig,
    TravelEntry,
    UnavailabilityInterval,
)


@dataclass(slots=True)
class StoredScheduleRecord:
    """Stored run result alongside input context enabling deterministic re-optimization."""

    result: ScheduleRunResult
    jobs: list[Job]
    electricians: list[Electrician]
    travel_times: list[TravelEntry]
    unavailability: list[UnavailabilityInterval]
    existing_assignments: list[ExistingAssignment]


class ScheduleRunRepository(Protocol):
    """Persistence contract separating FastAPI routes from storage implementation."""

    def save(self, record: StoredScheduleRecord) -> None: ...

    def get(self, run_id: str) -> StoredScheduleRecord | None: ...

    def get_latest(self) -> StoredScheduleRecord | None: ...


class InMemoryScheduleRunStore:
    """Validated in-memory repository used until shared DB persistence is wired."""

    def __init__(self) -> None:
        self._records: dict[str, StoredScheduleRecord] = {}
        self._latest_id: str | None = None

    def save(self, record: StoredScheduleRecord) -> None:
        run_id = record.result.run_id
        self._records[run_id] = record
        self._latest_id = run_id

    def get(self, run_id: str) -> StoredScheduleRecord | None:
        return self._records.get(run_id)

    def get_latest(self) -> StoredScheduleRecord | None:
        if self._latest_id is None:
            return None
        return self._records.get(self._latest_id)


def get_schedule_store(request: Request) -> ScheduleRunRepository:
    """FastAPI dependency retrieving the active ScheduleRunRepository from app.state."""
    store = getattr(request.app.state, "schedule_store", None)
    if store is None:
        store = InMemoryScheduleRunStore()
        request.app.state.schedule_store = store
    return store


router = APIRouter(prefix="/api/v1/scheduling", tags=["scheduling"])


def _resolve_inputs(
    use_bundled_dataset: bool,
    scenario_ids: list[str],
    electricians: list[Electrician] | None,
    jobs: list[Job] | None,
    travel_times: list[TravelEntry] | None,
    unavailability: list[UnavailabilityInterval] | None,
):
    """Resolve scheduling inputs from request payload or bundled CSV dataset."""
    bundle = None
    if use_bundled_dataset and (electricians is None or jobs is None or travel_times is None):
        bundle = load_dataset_bundle(scenario_ids=scenario_ids)
        if bundle.missing_files and (not bundle.electricians or not bundle.jobs):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Required dataset files missing: {', '.join(bundle.missing_files)}",
            )
        known_scenarios = {s.scenario_id for s in bundle.scenarios}
        unknown_scenarios = [sid for sid in scenario_ids if sid not in known_scenarios]
        if unknown_scenarios:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown disruption scenario_id(s): {', '.join(unknown_scenarios)}",
            )
        resolved_elecs = electricians if electricians is not None else bundle.electricians
        resolved_jobs = jobs if jobs is not None else bundle.jobs
        resolved_tt = travel_times if travel_times is not None else bundle.travel_entries
        resolved_unavail = unavailability if unavailability is not None else bundle.unavailability
        return resolved_elecs, resolved_jobs, resolved_tt, resolved_unavail, bundle

    if electricians is None or jobs is None or travel_times is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "When use_bundled_dataset is False, 'electricians', 'jobs', and 'travel_times' "
                "must all be provided explicitly."
            ),
        )
    if not electricians:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one electrician is required to generate a schedule.",
        )

    return electricians, jobs, travel_times, list(unavailability or []), None


def _build_metrics_response(res: ScheduleRunResult) -> ScheduleMetricsResponse:
    fin = res.final_schedule
    return ScheduleMetricsResponse(
        run_id=res.run_id,
        created_at_utc=res.created_at_utc,
        is_valid_for_commitment=res.is_valid_for_commitment,
        assigned_count=len(fin.assigned_job_ids),
        unassigned_count=len(fin.unassigned_job_ids),
        high_priority_unassigned_count=fin.high_priority_unassigned_count,
        total_travel_min=fin.total_travel_min,
        total_service_min=fin.total_service_min,
        hard_constraint_violation_count=fin.hard_constraint_violation_count,
        hard_sla_violation_count=fin.hard_sla_violation_count,
        predicted_soft_sla_breach_count=fin.predicted_soft_sla_breach_count,
        mean_soft_sla_urgency=fin.mean_soft_sla_urgency,
        max_soft_sla_urgency=fin.max_soft_sla_urgency,
        initial_objective=res.initial_greedy_schedule.objective,
        final_objective=fin.objective,
        technician_workloads=fin.technician_workloads,
        optimization=res.optimization,
        validation_warnings=res.validation_warnings,
    )


@router.get(
    "/audit",
    response_model=DatasetAuditReport,
    summary="Generate mandatory feasibility audit for bundled dataset",
)
def get_dataset_feasibility_audit(
    scenario_ids: list[str] = Query(default_factory=list),
) -> DatasetAuditReport:
    bundle = load_dataset_bundle(scenario_ids=scenario_ids)
    known_scenarios = {s.scenario_id for s in bundle.scenarios}
    unknown = [sid for sid in scenario_ids if sid not in known_scenarios]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scenario_id(s): {', '.join(unknown)}",
        )
    return generate_dataset_audit(bundle=bundle)


@router.post(
    "/generate",
    response_model=ScheduleRunResult,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an initial greedy schedule and optionally optimize it",
)
def create_schedule(
    payload: GenerateScheduleRequest,
    store: ScheduleRunRepository = Depends(get_schedule_store),
) -> ScheduleRunResult:
    elecs, jobs, tt, unavail, bundle = _resolve_inputs(
        use_bundled_dataset=payload.use_bundled_dataset,
        scenario_ids=payload.scenario_ids,
        electricians=payload.electricians,
        jobs=payload.jobs,
        travel_times=payload.travel_times,
        unavailability=payload.unavailability,
    )

    result = generate_schedule(
        jobs=jobs,
        electricians=elecs,
        travel_times=tt,
        existing_assignments=payload.existing_assignments,
        unavailability=unavail,
        config=payload.config,
        run_id=payload.run_id,
        active_scenario_ids=payload.scenario_ids,
        include_dataset_audit=payload.include_dataset_audit,
        dataset_bundle=bundle,
    )
    store.save(
        StoredScheduleRecord(
            result=result,
            jobs=jobs,
            electricians=elecs,
            travel_times=tt,
            unavailability=unavail,
            existing_assignments=payload.existing_assignments,
        )
    )
    return result


@router.post(
    "/optimize",
    response_model=ScheduleRunResult,
    summary="Optimize an existing run or newly supplied schedule inputs via local search",
)
def optimize_schedule(
    payload: OptimizeScheduleRequest,
    store: ScheduleRunRepository = Depends(get_schedule_store),
) -> ScheduleRunResult:
    if payload.run_id is not None and payload.jobs is None and payload.electricians is None and not payload.use_bundled_dataset:
        stored = store.get(payload.run_id)
        if stored is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule run '{payload.run_id}' not found.",
            )
        cfg: SchedulerConfig = (
            payload.config_overrides.model_copy(update={"enable_optimization": True})
            if payload.config_overrides is not None
            else stored.result.config.model_copy(update={"enable_optimization": True})
        )
        if cfg.max_iterations == 0:
            cfg = cfg.model_copy(update={"max_iterations": 100})

        result = generate_schedule(
            jobs=stored.jobs,
            electricians=stored.electricians,
            travel_times=stored.travel_times,
            existing_assignments=payload.existing_assignments or stored.existing_assignments,
            unavailability=stored.unavailability,
            config=cfg,
            active_scenario_ids=stored.result.active_scenario_ids,
        )
        store.save(
            StoredScheduleRecord(
                result=result,
                jobs=stored.jobs,
                electricians=stored.electricians,
                travel_times=stored.travel_times,
                unavailability=stored.unavailability,
                existing_assignments=payload.existing_assignments or stored.existing_assignments,
            )
        )
        return result

    elecs, jobs, tt, unavail, bundle = _resolve_inputs(
        use_bundled_dataset=payload.use_bundled_dataset,
        scenario_ids=payload.scenario_ids,
        electricians=payload.electricians,
        jobs=payload.jobs,
        travel_times=payload.travel_times,
        unavailability=payload.unavailability,
    )
    cfg = (
        payload.config_overrides.model_copy(update={"enable_optimization": True})
        if payload.config_overrides is not None
        else SchedulerConfig(enable_optimization=True)
    )
    result = generate_schedule(
        jobs=jobs,
        electricians=elecs,
        travel_times=tt,
        existing_assignments=payload.existing_assignments,
        unavailability=unavail,
        config=cfg,
        run_id=payload.run_id,
        active_scenario_ids=payload.scenario_ids,
        dataset_bundle=bundle,
    )
    store.save(
        StoredScheduleRecord(
            result=result,
            jobs=jobs,
            electricians=elecs,
            travel_times=tt,
            unavailability=unavail,
            existing_assignments=payload.existing_assignments,
        )
    )
    return result


@router.get(
    "/current",
    response_model=ScheduleRunResult,
    summary="Retrieve the most recent schedule run",
)
def get_current_schedule(
    store: ScheduleRunRepository = Depends(get_schedule_store),
) -> ScheduleRunResult:
    latest = store.get_latest()
    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No schedule has been generated yet.",
        )
    return latest.result


@router.get(
    "/current/metrics",
    response_model=ScheduleMetricsResponse,
    summary="Retrieve metrics and objective comparison for the most recent schedule",
)
def get_current_schedule_metrics(
    store: ScheduleRunRepository = Depends(get_schedule_store),
) -> ScheduleMetricsResponse:
    latest = store.get_latest()
    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No schedule has been generated yet.",
        )
    return _build_metrics_response(latest.result)


@router.get(
    "/current/explanations",
    response_model=ScheduleExplanationsResponse,
    summary="Retrieve assignment explanations and unassigned reasons for the latest schedule",
)
def get_current_schedule_explanations(
    store: ScheduleRunRepository = Depends(get_schedule_store),
) -> ScheduleExplanationsResponse:
    latest = store.get_latest()
    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No schedule has been generated yet.",
        )
    res = latest.result
    return ScheduleExplanationsResponse(
        run_id=res.run_id,
        created_at_utc=res.created_at_utc,
        assigned_explanations=res.explanations,
        unassigned_reasons=res.unassigned_reasons,
    )


@router.get(
    "/runs/{run_id}",
    response_model=ScheduleRunResult,
    summary="Retrieve a specific schedule run by run_id",
)
def get_schedule_by_run_id(
    run_id: str,
    store: ScheduleRunRepository = Depends(get_schedule_store),
) -> ScheduleRunResult:
    stored = store.get(run_id)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule run '{run_id}' not found.",
        )
    return stored.result


@router.get(
    "/runs/{run_id}/metrics",
    response_model=ScheduleMetricsResponse,
    summary="Retrieve metrics and objective breakdown for a specific run_id",
)
def get_run_metrics(
    run_id: str,
    store: ScheduleRunRepository = Depends(get_schedule_store),
) -> ScheduleMetricsResponse:
    stored = store.get(run_id)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule run '{run_id}' not found.",
        )
    return _build_metrics_response(stored.result)


@router.get(
    "/runs/{run_id}/explanations",
    response_model=ScheduleExplanationsResponse,
    summary="Retrieve assignment explanations and unassigned diagnostics for a specific run_id",
)
def get_run_explanations(
    run_id: str,
    store: ScheduleRunRepository = Depends(get_schedule_store),
) -> ScheduleExplanationsResponse:
    stored = store.get(run_id)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule run '{run_id}' not found.",
        )
    res = stored.result
    return ScheduleExplanationsResponse(
        run_id=res.run_id,
        created_at_utc=res.created_at_utc,
        assigned_explanations=res.explanations,
        unassigned_reasons=res.unassigned_reasons,
    )

