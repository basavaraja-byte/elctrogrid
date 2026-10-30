"""FastAPI routes for Technician Assignment Dispatch, 5-Minute Timeout, Acceptance/Rejection, and Retry."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from app.api.routes.scheduling import ScheduleRunRepository, get_schedule_store
from app.scheduler.dispatch import (
    DispatchConflictError,
    DispatchError,
    DispatchSession,
    DispatchSessionStore,
    OfferNotFoundError,
    StaleOfferError,
)
from app.schemas.dispatch_recovery import (
    DispatchActionResponse,
    DispatchStateSnapshot,
    InitializeDispatchRequest,
    OfferJobRequest,
    SweepTimeoutsRequest,
    TechnicianOfferResponseRequest,
)


def get_dispatch_store(request: Request) -> DispatchSessionStore:
    """FastAPI dependency retrieving the active DispatchSessionStore from app.state."""
    store = getattr(request.app.state, "dispatch_store", None)
    if store is None:
        store = DispatchSessionStore()
        request.app.state.dispatch_store = store
    return store


router = APIRouter(prefix="/api/v1/scheduling/dispatch", tags=["dispatch"])


def _get_session_or_404(run_id: str, dispatch_store: DispatchSessionStore) -> DispatchSession:
    session = dispatch_store.get(run_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispatch session for run '{run_id}' not initialized.",
        )
    return session


def _translate_dispatch_error(exc: DispatchError) -> HTTPException:
    if isinstance(exc, OfferNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"[{exc.error_code}] {exc.message}",
        )
    if isinstance(exc, (StaleOfferError, DispatchConflictError)):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"[{exc.error_code}] {exc.message}",
        )
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"[{exc.error_code}] {exc.message}",
    )


@router.post(
    "/runs/{run_id}/init",
    response_model=DispatchStateSnapshot,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize technician offer/timeout/retry tracking for a schedule run",
)
def initialize_dispatch_session(
    run_id: str,
    payload: InitializeDispatchRequest = Body(default_factory=InitializeDispatchRequest),
    schedule_store: ScheduleRunRepository = Depends(get_schedule_store),
    dispatch_store: DispatchSessionStore = Depends(get_dispatch_store),
) -> DispatchStateSnapshot:
    stored = schedule_store.get(run_id)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule run '{run_id}' not found.",
        )
    try:
        session = DispatchSession(
            schedule_result=stored.result,
            jobs=stored.jobs,
            electricians=stored.electricians,
            travel_times=stored.travel_times,
            unavailability=stored.unavailability,
            existing_assignments=stored.existing_assignments,
            dispatch_config=payload.dispatch_config,
            now_utc=payload.now_utc,
            auto_offer_all=payload.auto_offer_all,
        )
    except DispatchError as exc:
        raise _translate_dispatch_error(exc) from exc

    dispatch_store.put(session)
    return session.snapshot()


@router.get(
    "/runs/{run_id}",
    response_model=DispatchStateSnapshot,
    summary="Retrieve live dispatch offer state, audit events, and re-validated schedule",
)
def get_dispatch_state(
    run_id: str,
    dispatch_store: DispatchSessionStore = Depends(get_dispatch_store),
) -> DispatchStateSnapshot:
    session = _get_session_or_404(run_id, dispatch_store)
    return session.snapshot()


@router.post(
    "/runs/{run_id}/offer/{job_id}",
    response_model=DispatchActionResponse,
    summary="Issue a 5-minute assignment offer for a single scheduled or retryable job",
)
def issue_job_offer(
    run_id: str,
    job_id: str,
    payload: OfferJobRequest = Body(default_factory=OfferJobRequest),
    dispatch_store: DispatchSessionStore = Depends(get_dispatch_store),
) -> DispatchActionResponse:
    session = _get_session_or_404(run_id, dispatch_store)
    try:
        offer = session.offer_job(job_id=job_id, now_utc=payload.now_utc)
    except DispatchError as exc:
        raise _translate_dispatch_error(exc) from exc

    return DispatchActionResponse(
        run_id=session.run_id,
        action="offer_issued" if offer is not None else "candidates_exhausted",
        affected_job_ids=[job_id],
        new_offers=[offer] if offer is not None else [],
        exhausted_job_ids=[] if offer is not None else [job_id],
        state=session.snapshot(),
    )


@router.post(
    "/runs/{run_id}/respond",
    response_model=DispatchActionResponse,
    summary="Record technician acceptance or rejection with stale-offer and 5-minute timeout checks",
)
def respond_to_assignment_offer(
    run_id: str,
    payload: TechnicianOfferResponseRequest,
    dispatch_store: DispatchSessionStore = Depends(get_dispatch_store),
) -> DispatchActionResponse:
    session = _get_session_or_404(run_id, dispatch_store)
    try:
        return session.respond_to_offer(
            offer_id=payload.offer_id,
            technician_id=payload.technician_id,
            decision=payload.decision,
            reason=payload.reason,
            responded_at_utc=payload.responded_at_utc,
        )
    except DispatchError as exc:
        raise _translate_dispatch_error(exc) from exc


@router.post(
    "/runs/{run_id}/sweep-timeouts",
    response_model=DispatchActionResponse,
    summary="Expire pending offers past the 5-minute timeout and attempt next eligible technicians",
)
def sweep_expired_offers(
    run_id: str,
    payload: SweepTimeoutsRequest = Body(default_factory=SweepTimeoutsRequest),
    dispatch_store: DispatchSessionStore = Depends(get_dispatch_store),
) -> DispatchActionResponse:
    session = _get_session_or_404(run_id, dispatch_store)
    try:
        return session.sweep_timeouts(now_utc=payload.now_utc)
    except DispatchError as exc:
        raise _translate_dispatch_error(exc) from exc

