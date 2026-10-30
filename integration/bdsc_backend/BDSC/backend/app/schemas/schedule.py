"""Pydantic v2 schemas for shared scheduling, recovery, approval, candidate ranking, and metrics contracts."""

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import (
    AssignmentChangeType,
    ExecutionStatus,
    ScheduleVersionStatus,
    SchedulingRunType,
    SchedulingStrategy,
    SLARiskLevel,
)
from app.schemas.assignment import AssignmentResponse, ProposedAssignmentInput
from app.schemas.common import AuditLogResponse, ConstraintViolationSchema
from app.utils.validators import ensure_timezone_aware


class UnassignedJobReasonSchema(BaseModel):
    """Reason why a job remained unassigned in a scheduling run."""

    job_id: uuid.UUID
    reason_code: str = Field(..., min_length=1, max_length=64)
    explanation: str = Field(..., min_length=1, max_length=1000)


class SLARiskInfoSchema(BaseModel):
    """SLA risk analysis for an assigned job."""

    job_id: uuid.UUID
    sla_deadline: datetime
    planned_end_time: datetime
    buffer_minutes: int
    risk_level: SLARiskLevel
    is_late: bool


class ScheduleVersionResponse(BaseModel):
    """Response schema for ScheduleVersion."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    status: ScheduleVersionStatus
    created_at: datetime
    created_by: str
    parent_version_id: uuid.UUID | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    decision_reason: str | None = None


class SchedulingRunResponse(BaseModel):
    """Response schema for SchedulingRun."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    schedule_version_id: uuid.UUID | None = None
    idempotency_key: str
    run_type: SchedulingRunType
    strategy: SchedulingStrategy
    execution_status: ExecutionStatus
    total_jobs: int
    assigned_jobs: int
    unassigned_jobs: int
    total_travel_minutes: int
    estimated_late_jobs: int
    execution_time_ms: int
    unassigned_details: list[dict[str, Any]] = Field(default_factory=list)
    sla_risks: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


class ScheduleGenerateRequest(BaseModel):
    """Request schema for POST /api/v1/schedules/generate."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "idempotency_key": "sched-run-2026-10-30-001",
                "run_type": "INITIAL",
                "strategy": "BALANCED",
                "horizon_start": "2026-10-30T08:00:00+05:30",
                "horizon_end": "2026-10-30T20:00:00+05:30",
                "job_ids": None,
                "parent_version_id": None,
                "created_by": "scheduler_engine",
                "auto_activate": False,
                "proposed_assignments": None,
                "unassigned_reasons": None,
            }
        }
    )

    idempotency_key: str = Field(..., min_length=3, max_length=150)
    run_type: SchedulingRunType = Field(default=SchedulingRunType.INITIAL)
    strategy: SchedulingStrategy = Field(default=SchedulingStrategy.BALANCED)
    horizon_start: datetime
    horizon_end: datetime
    job_ids: list[uuid.UUID] | None = None
    parent_version_id: uuid.UUID | None = None
    created_by: str = Field(default="scheduler_engine", min_length=1, max_length=100)
    auto_activate: bool = Field(default=False)
    use_ai_durations: bool = Field(default=False, description="Whether to refine job durations using AI duration prediction")
    proposed_assignments: list[ProposedAssignmentInput] | None = None
    unassigned_reasons: list[UnassignedJobReasonSchema] | None = None

    @field_validator("parent_version_id", mode="before")
    @classmethod
    def normalize_optional_parent_uuid(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @model_validator(mode="after")
    def validate_horizon(self) -> "ScheduleGenerateRequest":
        hs = ensure_timezone_aware(self.horizon_start)
        he = ensure_timezone_aware(self.horizon_end)
        if he <= hs:
            raise ValueError("horizon_end must be strictly after horizon_start.")
        self.horizon_start = hs
        self.horizon_end = he
        return self


class ScheduleGenerationResponse(BaseModel):
    """Canonical shared scheduling contract response."""

    schedule_version: ScheduleVersionResponse
    scheduling_run: SchedulingRunResponse | None = None
    assignments: list[AssignmentResponse]
    unassigned_jobs: list[uuid.UUID]
    unassigned_reasons: list[UnassignedJobReasonSchema]
    total_travel_minutes: int
    assigned_job_count: int
    unassigned_job_count: int
    sla_risk_information: list[SLARiskInfoSchema]
    audit_logs: list[AuditLogResponse] = Field(default_factory=list)


class ScheduleApproveRequest(BaseModel):
    """Request schema for POST /api/v1/schedules/{schedule_id}/approve."""

    approved_by: str = Field(..., min_length=2, max_length=100)
    reason: str = Field(
        default="Schedule proposal reviewed and approved by Operations Manager",
        min_length=3,
        max_length=1000,
    )


class ScheduleRejectRequest(BaseModel):
    """Request schema for POST /api/v1/schedules/{schedule_id}/reject."""

    rejected_by: str = Field(..., min_length=2, max_length=100)
    reason: str = Field(..., min_length=3, max_length=1000)


class TechnicianWorkloadItem(BaseModel):
    """Workload breakdown for a single technician in a persisted schedule."""

    technician_id: uuid.UUID
    technician_name: str
    is_active: bool
    shift_duration_minutes: int
    assigned_job_count: int
    total_work_minutes: int
    total_travel_minutes: int
    total_busy_minutes: int
    utilization_pct: float


class WorkloadDistributionSummary(BaseModel):
    """Aggregate technician workload distribution statistics."""

    technicians_evaluated: int
    min_utilization_pct: float
    max_utilization_pct: float
    avg_utilization_pct: float
    std_dev_utilization_pct: float
    per_technician: list[TechnicianWorkloadItem]


class ScheduleMetricsResponse(BaseModel):
    """Persisted schedule metrics calculated from database records (Mandatory Addition #7)."""

    schedule_version_id: uuid.UUID
    version_number: int
    status: ScheduleVersionStatus
    total_jobs_in_scope: int
    assigned_jobs_count: int
    unassigned_jobs_count: int
    sla_compliant_count: int
    sla_at_risk_count: int
    sla_breached_count: int
    sla_compliance_rate_pct: float
    total_estimated_travel_minutes: int
    technician_workload_distribution: WorkloadDistributionSummary
    hard_constraint_violations_count: int
    hard_constraint_violations: list[ConstraintViolationSchema]


class AssignmentDiffItem(BaseModel):
    """Before-and-after comparison item for a single job across two schedule versions."""

    job_id: uuid.UUID
    job_status: str
    change_type: AssignmentChangeType
    base_technician_id: uuid.UUID | None = None
    target_technician_id: uuid.UUID | None = None
    base_planned_start_time: datetime | None = None
    target_planned_start_time: datetime | None = None
    base_planned_end_time: datetime | None = None
    target_planned_end_time: datetime | None = None
    time_shift_minutes: int = 0


class ScheduleMetricsDelta(BaseModel):
    """Quantitative delta between base and target schedules (target - base)."""

    assigned_jobs_delta: int
    unassigned_jobs_delta: int
    sla_compliance_rate_delta_pct: float
    total_travel_minutes_delta: int
    workload_std_dev_delta_pct: float
    hard_constraint_violations_delta: int


class ScheduleComparisonResponse(BaseModel):
    """Full before-and-after schedule comparison response."""

    base_schedule_id: uuid.UUID
    target_schedule_id: uuid.UUID
    base_version_number: int
    target_version_number: int
    base_metrics: ScheduleMetricsResponse
    target_metrics: ScheduleMetricsResponse
    deltas: ScheduleMetricsDelta
    changed_assignments_count: int
    unchanged_assignments_count: int
    assignment_changes: list[AssignmentDiffItem]


class CandidateRankingRequest(BaseModel):
    """Request schema for POST /api/v1/schedules/rank-candidates."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "11bc5c80-36b0-5d97-9498-2f72b19a2239",
                "planned_start_time": "2026-10-30T09:00:00+05:30",
                "reference_schedule_version_id": None,
            }
        }
    )

    job_id: uuid.UUID
    planned_start_time: datetime | None = None
    reference_schedule_version_id: uuid.UUID | None = None

    @field_validator("reference_schedule_version_id", mode="before")
    @classmethod
    def normalize_optional_ref_uuid(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @model_validator(mode="after")
    def normalize_start(self) -> "CandidateRankingRequest":
        if self.planned_start_time is not None:
            self.planned_start_time = ensure_timezone_aware(self.planned_start_time)
        return self


class RankedTechnicianCandidate(BaseModel):
    """Feasible technician candidate ranked by the multi-criteria heuristic."""

    rank: int
    technician_id: uuid.UUID
    technician_name: str
    planned_start_time: datetime
    planned_end_time: datetime
    estimated_travel_minutes: int
    composite_score: float
    component_scores: dict[str, float]
    explanation: str


class InfeasibleTechnicianCandidate(BaseModel):
    """Technician excluded from candidate ranking due to hard-constraint violations."""

    technician_id: uuid.UUID
    technician_name: str
    violations: list[ConstraintViolationSchema]


class CandidateRankingResponse(BaseModel):
    """Response schema for POST /api/v1/schedules/rank-candidates (Mandatory Addition #6)."""

    job_id: uuid.UUID
    is_globally_optimal: bool = False
    methodology_note: str = (
        "Feasibility-filtered multi-criteria local heuristic. Does not claim global optimality."
    )
    scoring_weights: dict[str, float]
    feasible_candidates: list[RankedTechnicianCandidate]
    infeasible_candidates: list[InfeasibleTechnicianCandidate]


class ScheduleValidationRequest(BaseModel):
    """Request schema for POST /api/v1/schedules/validate."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "parent_version_id": None,
                "proposed_assignments": [
                    {
                        "job_id": "11bc5c80-36b0-5d97-9498-2f72b19a2239",
                        "technician_id": "2c8d3073-36eb-5528-9287-12f86b2400be",
                        "planned_start_time": "2026-10-30T09:00:00+05:30",
                        "planned_end_time": "2026-10-30T10:00:00+05:30",
                        "estimated_travel_minutes": 15,
                        "assignment_status": "PLANNED",
                        "assignment_reason": "Proposed assignment validation",
                    }
                ],
            }
        }
    )

    parent_version_id: uuid.UUID | None = None
    proposed_assignments: list[ProposedAssignmentInput]

    @field_validator("parent_version_id", mode="before")
    @classmethod
    def normalize_optional_parent_uuid(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v


class ScheduleValidationResponse(BaseModel):
    """Response schema for POST /api/v1/schedules/validate."""

    is_valid: bool
    violations_count: int
    violations: list[ConstraintViolationSchema]

