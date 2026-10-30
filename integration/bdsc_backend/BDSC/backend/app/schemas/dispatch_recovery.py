"""Pydantic schemas for Technician Assignment Dispatch/Timeout/Retry and D01-D07 Disruption Recovery.

Extends `app.schemas.scheduling` without altering existing request/response contracts.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.scheduling import (
    AssignmentExplanation,
    ExistingAssignment,
    Job,
    PriorityLevel,
    ReasonCode,
    ScheduleRunResult,
    SchedulerConfig,
    ScheduleSnapshot,
    UnassignedJobReport,
)


# ---------------------------------------------------------------------------
# Assignment Dispatch, 5-Minute Timeout, Acceptance/Rejection & Retry Schemas
# ---------------------------------------------------------------------------

DEFAULT_ASSIGNMENT_TIMEOUT_SECONDS: int = 300  # 5 minutes (5 * 60s)


class OfferStatus(str, Enum):
    """Lifecycle states of a single technician assignment offer."""

    PENDING_RESPONSE = "pending_response"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class JobDispatchStatus(str, Enum):
    """Dispatch state of a job across sequential offer attempts."""

    LOCKED_COMMITTED = "locked_committed"
    PLANNED_UNOFFERED = "planned_unoffered"
    PENDING_RESPONSE = "pending_response"
    ACCEPTED = "accepted"
    EXHAUSTED_UNASSIGNED = "exhausted_unassigned"


class DispatchConfig(BaseModel):
    """Configuration for technician assignment offer timeout and automatic retry."""

    model_config = ConfigDict(extra="forbid")

    response_timeout_seconds: int = Field(
        default=DEFAULT_ASSIGNMENT_TIMEOUT_SECONDS,
        gt=0,
        description="Technician response deadline in seconds; defaults to 300s (5 minutes).",
    )
    auto_retry_on_reject: bool = Field(
        default=True,
        description="Automatically attempt the next eligible & feasible technician upon rejection.",
    )
    auto_retry_on_timeout: bool = Field(
        default=True,
        description="Automatically attempt the next eligible & feasible technician upon 5-minute timeout.",
    )


class RejectedCandidateSummary(BaseModel):
    """Diagnostic summary of a rejected or ineligible candidate technician/slot."""

    technician_id: str
    reason_code: ReasonCode
    detail: str


class AssignmentOffer(BaseModel):
    """Single versioned assignment offer issued to an eligible technician."""

    offer_id: str
    run_id: str
    job_id: str
    technician_id: str
    attempt_number: int = Field(..., ge=1)
    status: OfferStatus
    route_position: int
    from_location_id: str
    planned_departure_min: int
    planned_arrival_min: int
    planned_start_min: int
    planned_completion_min: int
    travel_time_min: int
    offered_at_utc: datetime
    expires_at_utc: datetime
    responded_at_utc: datetime | None = None
    response_reason: str | None = None
    selection_explanation: AssignmentExplanation | None = None
    rejected_alternatives: list[RejectedCandidateSummary] = Field(default_factory=list)


class DispatchTransitionEvent(BaseModel):
    """Immutable audit log entry for offers, acceptances, rejections, timeouts, and retries."""

    event_id: str
    timestamp_utc: datetime
    job_id: str
    event_type: Literal[
        "offer_issued",
        "offer_accepted",
        "offer_rejected",
        "offer_timed_out",
        "retry_offer_issued",
        "candidates_exhausted",
        "stale_or_conflicting_attempt_blocked",
    ]
    offer_id: str | None = None
    technician_id: str | None = None
    attempt_number: int | None = None
    next_offer_id: str | None = None
    next_technician_id: str | None = None
    summary: str


class JobDispatchRecord(BaseModel):
    """Per-job dispatch tracking state including full attempt history."""

    job_id: str
    priority: PriorityLevel
    dispatch_status: JobDispatchStatus
    assigned_technician_id: str | None = None
    planned_start_min: int | None = None
    planned_completion_min: int | None = None
    active_offer_id: str | None = None
    attempts_made: int = 0
    excluded_technician_ids: list[str] = Field(default_factory=list)
    offers: list[AssignmentOffer] = Field(default_factory=list)
    final_unassigned_reason: UnassignedJobReport | None = None


class DispatchStateSnapshot(BaseModel):
    """Complete live dispatch state, active offers, audit log, and re-validated schedule."""

    run_id: str
    dispatch_config: DispatchConfig
    created_at_utc: datetime
    last_updated_utc: datetime
    is_valid_for_commitment: bool
    pending_offer_count: int
    accepted_count: int
    locked_committed_count: int
    exhausted_unassigned_count: int
    job_states: dict[str, JobDispatchRecord]
    events: list[DispatchTransitionEvent]
    current_schedule: ScheduleSnapshot


class InitializeDispatchRequest(BaseModel):
    """Request payload to initialize dispatch tracking on a schedule run."""

    model_config = ConfigDict(extra="forbid")

    auto_offer_all: bool = Field(
        default=True,
        description="Immediately issue 5-minute offers for all newly scheduled unlocked jobs.",
    )
    now_utc: datetime | None = None
    dispatch_config: DispatchConfig = Field(default_factory=DispatchConfig)


class OfferJobRequest(BaseModel):
    """Request payload to issue an assignment offer for a single job."""

    model_config = ConfigDict(extra="forbid")

    now_utc: datetime | None = None


class TechnicianOfferResponseRequest(BaseModel):
    """Request payload for a technician accepting or rejecting an offer."""

    model_config = ConfigDict(extra="forbid")

    offer_id: str = Field(..., min_length=1)
    technician_id: str = Field(..., min_length=1)
    decision: Literal["accept", "reject"]
    reason: str | None = None
    responded_at_utc: datetime | None = None


class SweepTimeoutsRequest(BaseModel):
    """Request payload to evaluate expired 5-minute offers and trigger retries."""

    model_config = ConfigDict(extra="forbid")

    now_utc: datetime | None = None


class DispatchActionResponse(BaseModel):
    """Structured result of an offer, accept/reject response, or timeout sweep."""

    run_id: str
    action: str
    affected_job_ids: list[str] = Field(default_factory=list)
    timed_out_offer_ids: list[str] = Field(default_factory=list)
    new_offers: list[AssignmentOffer] = Field(default_factory=list)
    exhausted_job_ids: list[str] = Field(default_factory=list)
    state: DispatchStateSnapshot


# ---------------------------------------------------------------------------
# Disruption Recovery & Simulation Schemas (D01-D07)
# ---------------------------------------------------------------------------


class RecoveryActionType(str, Enum):
    """Classification of per-job actions taken during disruption recovery."""

    PRESERVED_COMPLETED = "preserved_completed"
    PRESERVED_IN_PROGRESS = "preserved_in_progress"
    PRESERVED_LOCKED_FUTURE = "preserved_locked_future"
    DURATION_EXTENDED_IN_PROGRESS = "duration_extended_in_progress"
    UNCHANGED_ASSIGNMENT = "unchanged_assignment"
    RESCHEDULED_TIME = "rescheduled_time"
    REASSIGNED_TECHNICIAN = "reassigned_technician"
    NEWLY_INSERTED_URGENT = "newly_inserted_urgent"
    BACKFILLED_FREED_CAPACITY = "backfilled_freed_capacity"
    CANCELLED_REMOVED = "cancelled_removed"
    DEDUPLICATED_REQUEST = "deduplicated_request"
    LEFT_UNASSIGNED = "left_unassigned"
    UNASSIGNED_AFTER_DISRUPTION = "unassigned_after_disruption"


class ScenarioSpecification(BaseModel):
    """Formal specification of a disruption scenario (D01-D07) derived from dataset metadata."""

    scenario_id: str
    scenario_name: str
    event_type: str
    target_id: str
    event_time_min: int
    event_time_hhmm: str
    payload: str
    trigger_description: str
    expected_affected_entities: list[str]
    expected_recovery_action: str
    enforced_constraints: list[str]
    expected_outcome: str


class JobRecoveryExplanation(BaseModel):
    """Grounded explanation of how and why a job was preserved, moved, added, or unassigned."""

    job_id: str
    action_type: RecoveryActionType
    previous_technician_id: str | None = None
    new_technician_id: str | None = None
    previous_start_min: int | None = None
    new_start_min: int | None = None
    previous_completion_min: int | None = None
    new_completion_min: int | None = None
    explanation: str
    rejected_candidates: list[RejectedCandidateSummary] = Field(default_factory=list)


class ScenarioRecoveryResult(BaseModel):
    """Complete reproducible result of simulating or executing a disruption recovery."""

    scenario_id: str
    scenario_name: str
    event_type: str
    target_id: str
    event_time_min: int
    event_time_hhmm: str
    idempotency_key: str | None = None
    idempotent_replay: bool = False
    duplicate_request_suppressed: bool = False
    specification: ScenarioSpecification
    affected_job_ids: list[str] = Field(default_factory=list)
    affected_technician_ids: list[str] = Field(default_factory=list)
    preserved_completed_job_ids: list[str] = Field(default_factory=list)
    preserved_in_progress_job_ids: list[str] = Field(default_factory=list)
    preserved_locked_future_job_ids: list[str] = Field(default_factory=list)
    reassigned_job_ids: list[str] = Field(default_factory=list)
    rescheduled_job_ids: list[str] = Field(default_factory=list)
    newly_assigned_job_ids: list[str] = Field(default_factory=list)
    cancelled_job_ids: list[str] = Field(default_factory=list)
    newly_unassigned_job_ids: list[str] = Field(default_factory=list)
    recovery_summary: str
    job_recovery_explanations: dict[str, JobRecoveryExplanation] = Field(default_factory=dict)
    baseline_run_id: str
    recovered_schedule_run: ScheduleRunResult
    validation_passed: bool
    validation_errors: list[str] = Field(default_factory=list)
    objective_consistent: bool


class SimulateScenarioRequest(BaseModel):
    """Request payload to simulate a disruption scenario (D01-D07) from baseline or an existing run."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(..., min_length=1, description="Scenario identifier, e.g. 'D01'..'D07'.")
    baseline_run_id: str | None = Field(
        default=None,
        description="Optional stored baseline run_id; when omitted, baseline is generated deterministically.",
    )
    locked_future_job_ids: list[str] = Field(
        default_factory=list,
        description="Optional future job IDs to lock (locked=True) prior to recovery.",
    )
    existing_assignments_override: list[ExistingAssignment] | None = None
    idempotency_key: str | None = None
    config: SchedulerConfig = Field(default_factory=SchedulerConfig)


class SimulateAllScenariosRequest(BaseModel):
    """Request payload to execute the reproducible D01-D07 simulation suite."""

    model_config = ConfigDict(extra="forbid")

    scenario_ids: list[str] = Field(
        default_factory=lambda: ["D01", "D02", "D03", "D04", "D05", "D06", "D07"]
    )
    config: SchedulerConfig = Field(default_factory=SchedulerConfig)


class SimulateAllScenariosResponse(BaseModel):
    """Aggregated result of simulating multiple disruption scenarios reproducibly."""

    baseline_run_id: str
    baseline_assigned_count: int
    baseline_unassigned_count: int
    all_validations_passed: bool
    all_objectives_consistent: bool
    results_by_scenario: dict[str, ScenarioRecoveryResult]


class IdempotentJobSubmissionRequest(BaseModel):
    """Idempotent job intake request supporting D06 duplicate-request protection via API."""

    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(..., min_length=1)
    job: Job
    baseline_run_id: str | None = None
    event_time_min: int | None = None
    reschedule_immediately: bool = Field(default=True)
    config: SchedulerConfig = Field(default_factory=SchedulerConfig)


class IdempotentJobSubmissionResponse(BaseModel):
    """Outcome of an idempotent job creation / scheduling submission."""

    idempotency_key: str
    job_id: str
    created: bool
    duplicate_suppressed: bool
    schedule_run: ScheduleRunResult | None = None
    message: str

