"""Shared Pydantic schemas and domain contracts for DispatchGrid Modules B & C.

Designed for clean interoperability with:
- Module A (Job & Technician Management / Persistence)
- Module D (Disruption Recovery)
- Operations Manager Dashboard (Frontend)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PriorityLevel(str, Enum):
    """Canonical business priorities ordered from highest (Critical) to lowest (Low).

    Mapping from P1-P4 notation and synthetic CSV labels:
    - P1 Critical -> PriorityLevel.CRITICAL (rank 1)
    - P2 High     -> PriorityLevel.HIGH     (rank 2)
    - P3 Medium   -> PriorityLevel.NORMAL   (rank 3; CSV uses 'Normal')
    - P4 Low      -> PriorityLevel.LOW      (rank 4)
    """

    CRITICAL = "Critical"
    HIGH = "High"
    NORMAL = "Normal"
    LOW = "Low"

    @property
    def rank(self) -> int:
        return _PRIORITY_RANK[self]

    @property
    def is_high_or_critical(self) -> bool:
        return self in (PriorityLevel.CRITICAL, PriorityLevel.HIGH)


_PRIORITY_RANK: dict[PriorityLevel, int] = {
    PriorityLevel.CRITICAL: 1,
    PriorityLevel.HIGH: 2,
    PriorityLevel.NORMAL: 3,
    PriorityLevel.LOW: 4,
}

_PRIORITY_ALIASES: dict[str, PriorityLevel] = {
    "critical": PriorityLevel.CRITICAL,
    "p1": PriorityLevel.CRITICAL,
    "p1 critical": PriorityLevel.CRITICAL,
    "p1_critical": PriorityLevel.CRITICAL,
    "high": PriorityLevel.HIGH,
    "p2": PriorityLevel.HIGH,
    "p2 high": PriorityLevel.HIGH,
    "p2_high": PriorityLevel.HIGH,
    "normal": PriorityLevel.NORMAL,
    "medium": PriorityLevel.NORMAL,
    "p3": PriorityLevel.NORMAL,
    "p3 medium": PriorityLevel.NORMAL,
    "p3_medium": PriorityLevel.NORMAL,
    "p3 normal": PriorityLevel.NORMAL,
    "low": PriorityLevel.LOW,
    "p4": PriorityLevel.LOW,
    "p4 low": PriorityLevel.LOW,
    "p4_low": PriorityLevel.LOW,
}


def normalize_priority(value: str | PriorityLevel) -> PriorityLevel:
    """Map dataset or P1-P4 priority strings to canonical PriorityLevel."""
    if isinstance(value, PriorityLevel):
        return value
    if not isinstance(value, str):
        raise ValueError(f"Unsupported priority type: {type(value)!r}")
    cleaned = value.strip().lower()
    if cleaned in _PRIORITY_ALIASES:
        return _PRIORITY_ALIASES[cleaned]
    raise ValueError(
        f"Unknown priority '{value}'. Expected Critical/P1, High/P2, Normal/Medium/P3, or Low/P4."
    )


class JobStatus(str, Enum):
    """Lifecycle status of a service job."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TechnicianStatus(str, Enum):
    """Operational status of a technician."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    OFF_DUTY = "off_duty"


class ReasonCode(str, Enum):
    """Stable diagnostic reason codes for candidate rejection and unassigned jobs."""

    MISSING_SKILL = "MISSING_SKILL"
    MISSING_CERTIFICATION = "MISSING_CERTIFICATION"
    ZONE_INELIGIBLE = "ZONE_INELIGIBLE"
    NO_AVAILABLE_SLOT = "NO_AVAILABLE_SLOT"
    SHIFT_CONSTRAINT = "SHIFT_CONSTRAINT"
    TRAVEL_CONFLICT = "TRAVEL_CONFLICT"
    SLA_DEADLINE_INFEASIBLE = "SLA_DEADLINE_INFEASIBLE"
    RESOURCE_CAPACITY_EXHAUSTED = "RESOURCE_CAPACITY_EXHAUSTED"
    INVALID_JOB_DATA = "INVALID_JOB_DATA"
    MISSING_TRAVEL_DATA = "MISSING_TRAVEL_DATA"


class TerminationReason(str, Enum):
    """Deterministic termination states for Module C local search."""

    OPTIMIZATION_DISABLED = "OPTIMIZATION_DISABLED"
    LOCAL_OPTIMUM_REACHED = "LOCAL_OPTIMUM_REACHED"
    MAX_ITERATIONS_REACHED = "MAX_ITERATIONS_REACHED"
    MAX_RUNTIME_REACHED = "MAX_RUNTIME_REACHED"
    CYCLE_PREVENTED = "CYCLE_PREVENTED"
    NO_MOVABLE_ASSIGNMENTS = "NO_MOVABLE_ASSIGNMENTS"


def minutes_to_hhmm(minutes: int) -> str:
    """Format minutes after midnight (e.g. 480 -> '08:00', 1020 -> '17:00')."""
    if minutes < 0:
        sign = "-"
        abs_m = abs(minutes)
        return f"{sign}{abs_m // 60:02d}:{abs_m % 60:02d}"
    days, rem = divmod(minutes, 1440)
    hh, mm = divmod(rem, 60)
    suffix = f" (+{days}d)" if days > 0 else ""
    return f"{hh:02d}:{mm:02d}{suffix}"


def minutes_to_utc_datetime(minutes: int, service_date: date) -> datetime:
    """Convert minutes after midnight on service_date into a timezone-aware UTC datetime."""
    midnight = datetime(
        service_date.year,
        service_date.month,
        service_date.day,
        0,
        0,
        0,
        tzinfo=timezone.utc,
    )
    return midnight + timedelta(minutes=minutes)


def datetime_to_service_minutes(dt: datetime, service_date: date) -> int:
    """Convert a timezone-aware datetime to integer minutes from service_date 00:00 UTC."""
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("Datetime values must be timezone-aware (naive datetime rejected).")
    utc_dt = dt.astimezone(timezone.utc)
    midnight = datetime(
        service_date.year,
        service_date.month,
        service_date.day,
        0,
        0,
        0,
        tzinfo=timezone.utc,
    )
    delta_seconds = (utc_dt - midnight).total_seconds()
    return int(round(delta_seconds / 60.0))


class Electrician(BaseModel):
    """Domain model for an electrician / field technician."""

    model_config = ConfigDict(extra="ignore")

    technician_id: str = Field(..., min_length=1)
    name: str = Field(default="")
    trade: str = Field(default="electrician")
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    eligible_zones: list[str] = Field(default_factory=list)
    home_zone: str | None = None
    shift_start_min: int
    shift_end_min: int
    start_x_km: float | None = None
    start_y_km: float | None = None
    start_location_id: str | None = None
    max_travel_per_leg_min: int | None = None
    status: str = Field(default="active")

    @field_validator("skills", "certifications", "eligible_zones", mode="before")
    @classmethod
    def _parse_pipe_or_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [tok.strip() for tok in value.split("|") if tok.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(tok).strip() for tok in value if str(tok).strip()]
        raise ValueError(f"Expected pipe-delimited string or list, got {type(value)!r}")

    @property
    def effective_start_location_id(self) -> str:
        return self.start_location_id or f"HOME_{self.technician_id}"

    @property
    def is_active(self) -> bool:
        return self.status.strip().lower() == TechnicianStatus.ACTIVE.value


class UnavailabilityInterval(BaseModel):
    """Time interval during which a technician cannot travel or perform work."""

    model_config = ConfigDict(extra="ignore")

    unavailability_id: str = Field(default="UNAVAIL")
    technician_id: str = Field(..., min_length=1)
    start_min: int
    end_min: int
    reason: str = Field(default="")
    scenario_id: str | None = None

    @model_validator(mode="after")
    def _validate_bounds(self) -> UnavailabilityInterval:
        if self.end_min < self.start_min:
            raise ValueError(
                f"Unavailability {self.unavailability_id} has end_min ({self.end_min}) < start_min ({self.start_min})."
            )
        return self


class Job(BaseModel):
    """Domain model for an electrical service job.

    Note: Domain-level job anomalies (such as duration_min <= 0 or inverted windows)
    are allowed to instantiate when constructed in engine workflows so Module B's
    validator can explicitly classify and report them as INVALID_JOB_DATA rather than
    crashing an entire batch schedule run. Strict API validation is enforced separately
    when requested.
    """

    model_config = ConfigDict(extra="ignore")

    job_id: str = Field(..., min_length=1)
    trade: str = Field(default="electrician")
    job_type: str = Field(default="")
    required_skills: list[str] = Field(default_factory=list)
    required_certifications: list[str] = Field(default_factory=list)
    priority: str = Field(default="Normal")
    duration_min: int
    zone: str = Field(default="")
    location_x_km: float | None = None
    location_y_km: float | None = None
    location_id: str | None = None
    window_start_min: int | None = None
    window_end_min: int | None = None
    sla_deadline_min: int | None = None
    window_start_dt: datetime | None = None
    window_end_dt: datetime | None = None
    sla_deadline_dt: datetime | None = None
    is_hard_deadline: bool | None = None
    status: str = Field(default="pending")
    notes: str = Field(default="")

    @field_validator("required_skills", "required_certifications", mode="before")
    @classmethod
    def _parse_pipe_or_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [tok.strip() for tok in value.split("|") if tok.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(tok).strip() for tok in value if str(tok).strip()]
        raise ValueError(f"Expected pipe-delimited string or list, got {type(value)!r}")

    @property
    def effective_location_id(self) -> str:
        return self.location_id or self.job_id

    def resolve_times(self, service_date: date) -> tuple[int | None, int | None, int | None]:
        """Resolve integer minutes from either *_min fields or timezone-aware *_dt fields."""
        ws = (
            self.window_start_min
            if self.window_start_min is not None
            else (
                datetime_to_service_minutes(self.window_start_dt, service_date)
                if self.window_start_dt is not None
                else None
            )
        )
        we = (
            self.window_end_min
            if self.window_end_min is not None
            else (
                datetime_to_service_minutes(self.window_end_dt, service_date)
                if self.window_end_dt is not None
                else None
            )
        )
        sla = (
            self.sla_deadline_min
            if self.sla_deadline_min is not None
            else (
                datetime_to_service_minutes(self.sla_deadline_dt, service_date)
                if self.sla_deadline_dt is not None
                else None
            )
        )
        return ws, we, sla


class TravelEntry(BaseModel):
    """Pairwise travel time and distance record."""

    model_config = ConfigDict(extra="ignore")

    from_location_id: str = Field(..., min_length=1)
    to_location_id: str = Field(..., min_length=1)
    travel_time_min: int
    distance_km_est: float = Field(default=0.0)
    estimate_type: str = Field(default="matrix_lookup")


class DisruptionScenario(BaseModel):
    """Scenario metadata loaded from disruption_scenarios.csv."""

    model_config = ConfigDict(extra="ignore")

    scenario_id: str
    scenario_name: str
    event_type: str
    target_id: str
    event_time_min: int
    payload: str = ""


class ExistingAssignment(BaseModel):
    """Pre-existing commitment passed into scheduling or disruption recovery.

    Invariants enforced by the engine:
    - status == 'completed': permanently fixed on technician and time interval.
    - status == 'in_progress': protected on technician and planned_start_min;
      completion_min adjusts if job.duration_min changed (e.g., Scenario D03).
    - locked == True: treated as a protected commitment and never moved or dropped.
    - status == 'assigned' and locked == False: baseline assignment eligible for
      re-optimization or recovery; changing it incurs schedule-change cost CR.
    """

    model_config = ConfigDict(extra="ignore")

    job_id: str = Field(..., min_length=1)
    technician_id: str = Field(..., min_length=1)
    departure_min: int | None = None
    arrival_min: int | None = None
    planned_start_min: int
    completion_min: int | None = None
    status: str = Field(default="assigned")
    locked: bool = Field(default=False)

    @property
    def is_protected(self) -> bool:
        st = self.status.strip().lower()
        return self.locked or st in (JobStatus.COMPLETED.value, JobStatus.IN_PROGRESS.value)


class SchedulerConfig(BaseModel):
    """Configurable policy, heuristic weights, normalization bounds, and search budgets.

    Note: Objective weights and urgency horizon are configurable engineering heuristics,
    not scientifically calibrated global constants.
    """

    model_config = ConfigDict(extra="forbid")

    service_date: date = Field(default=date(2026, 10, 30))

    # Deadline & constraint policies
    sla_mode: Literal["hard", "soft", "hard_critical_only"] = Field(
        default="hard",
        description=(
            "'hard': treat SLA deadline as a hard completion deadline unless job.is_hard_deadline is False; "
            "'soft': allow negative SLA slack and score soft-SLA risk/breaches; "
            "'hard_critical_only': enforce hard completion SLA on Critical jobs and soft SLA on others."
        ),
    )
    allow_overtime: bool = Field(default=False)
    max_overtime_min: int = Field(default=0, ge=0)
    allow_coordinate_travel_fallback: bool = Field(
        default=True,
        description=(
            "When True, if a location pair is absent from travel_times.csv (such as scenario job J101) "
            "and both endpoints have valid coordinates, compute travel time using the dataset README "
            "formula (planar distance * 1.25 road detour at 30 km/h, rounded up to 5-min increments) "
            "and emit an explicit validation warning. When False, missing pairs fail with MISSING_TRAVEL_DATA."
        ),
    )
    protect_in_progress: bool = Field(default=True)

    # Urgency & scarcity parameters
    urgency_horizon_min: float = Field(default=240.0, gt=0.0)
    dynamic_priority_reordering: bool = Field(
        default=True,
        description="Recompute feasible candidate counts and urgency dynamically within each priority tier.",
    )
    scarcity_protection_weight: float = Field(
        default=0.15,
        ge=0.0,
        description="Tie-breaking preference against consuming bottleneck technicians when flexible alternatives exist.",
    )

    # Normalized schedule-level objective weights: C = wT*CT + wS*CS + wW*CW + wR*CR
    w_travel: float = Field(default=0.40, ge=0.0)
    w_sla_risk: float = Field(default=0.30, ge=0.0)
    w_workload: float = Field(default=0.20, ge=0.0)
    w_recovery_change: float = Field(default=0.10, ge=0.0)

    # Normalization reference bounds (documented problem-scale constants)
    reference_travel_per_job_min: float = Field(default=60.0, gt=0.0)
    recovery_shift_norm_min: float = Field(default=120.0, gt=0.0)

    # Module C bounded local search parameters
    enable_optimization: bool = Field(default=True)
    max_iterations: int = Field(default=100, ge=0)
    max_runtime_seconds: float = Field(default=5.0, gt=0.0)


class AssignmentExplanation(BaseModel):
    """Evidence-based explanation for an assigned job."""

    job_id: str
    selected_technician_id: str
    planned_departure_min: int
    planned_arrival_min: int
    planned_start_min: int
    planned_completion_min: int
    travel_time_min: int
    incremental_travel_min: int
    route_position: int
    from_location_id: str
    to_location_id: str
    eligibility_reason: str
    selection_reason: str
    route_impact: str
    sla_deadline_min: int
    slack_min: int
    soft_sla_urgency: float
    deadline_risk_label: Literal["low", "moderate", "high", "critical_zero_slack", "soft_breach"]
    candidates_evaluated: int
    candidates_feasible: int
    rejected_summary_by_reason: dict[str, int] = Field(default_factory=dict)
    changed_during_optimization: bool = False
    optimization_change_note: str | None = None


class ScheduledAssignment(BaseModel):
    """Single validated job assignment on an electrician's route."""

    job_id: str
    technician_id: str
    priority: PriorityLevel
    route_position: int
    from_location_id: str
    departure_min: int
    arrival_min: int
    planned_start_min: int
    completion_min: int
    departure_hhmm: str
    arrival_hhmm: str
    planned_start_hhmm: str
    completion_hhmm: str
    planned_start_utc: datetime
    planned_arrival_utc: datetime
    planned_completion_utc: datetime
    travel_time_min: int
    incremental_travel_min: int
    service_duration_min: int
    sla_deadline_min: int
    slack_min: int
    soft_sla_urgency: float
    is_hard_deadline: bool
    travel_estimate_source: str = "matrix_lookup"
    status: str = "assigned"
    is_protected: bool = False
    changed_by_optimizer: bool = False
    explanation: AssignmentExplanation | None = None


class UnassignedJobReport(BaseModel):
    """Actionable diagnostic report explaining why a job remained unassigned."""

    job_id: str
    priority: str
    primary_reason_code: ReasonCode
    summary: str
    is_statically_eligible: bool
    static_eligible_count: int
    static_eligible_technician_ids: list[str] = Field(default_factory=list)
    isolated_feasible_count: int = 0
    rejection_counts_by_code: dict[str, int] = Field(default_factory=dict)
    supporting_details: list[str] = Field(default_factory=list)


class TechnicianWorkloadSummary(BaseModel):
    """Separate tracking of service workload and travel workload per technician."""

    technician_id: str
    assigned_job_count: int
    job_ids: list[str] = Field(default_factory=list)
    shift_start_min: int
    shift_end_min: int
    shift_duration_min: int
    planned_service_min: int
    planned_travel_min: int
    total_duty_min: int
    service_utilization: float
    duty_utilization: float
    overtime_min: int = 0


class ObjectiveBreakdown(BaseModel):
    """Detailed breakdown of all lexicographic and normalized weighted objective components."""

    weighted_cost: float
    travel_cost_norm: float
    soft_sla_risk_norm: float
    workload_imbalance_norm: float
    schedule_change_cost_norm: float
    w_travel: float
    w_sla_risk: float
    w_workload: float
    w_recovery_change: float
    raw_total_travel_min: int
    raw_total_service_min: int
    raw_total_soft_sla_urgency: float
    raw_service_utilization_std: float
    raw_total_overtime_min: int
    raw_schedule_change_units: float
    hard_violation_count: int
    protected_violation_count: int
    hard_sla_violation_count: int
    predicted_soft_sla_breach_count: int
    assigned_count: int
    unassigned_count: int
    unassigned_by_priority: dict[str, int] = Field(default_factory=dict)


class ScheduleSnapshot(BaseModel):
    """Complete metrics and assignments for either initial greedy or final optimized schedule."""

    stage: Literal["initial_greedy", "final_optimized"]
    assignments: list[ScheduledAssignment]
    assigned_job_ids: list[str]
    unassigned_job_ids: list[str]
    unassigned_reports: list[UnassignedJobReport]
    technician_workloads: list[TechnicianWorkloadSummary]
    total_travel_min: int
    total_service_min: int
    hard_constraint_violation_count: int
    hard_sla_violation_count: int
    predicted_soft_sla_breach_count: int
    mean_soft_sla_urgency: float
    max_soft_sla_urgency: float
    high_priority_unassigned_count: int
    objective: ObjectiveBreakdown
    is_valid_for_commitment: bool
    validation_errors: list[str] = Field(default_factory=list)


class OptimizationChangeRecord(BaseModel):
    """Diff record capturing an assignment change made during Module C optimization."""

    job_id: str
    change_type: Literal["newly_assigned", "reassigned_technician", "rescheduled_time_or_order"]
    previous_technician_id: str | None = None
    new_technician_id: str
    previous_start_min: int | None = None
    new_start_min: int
    note: str


class OptimizationSummary(BaseModel):
    """Execution telemetry and improvement comparison for Module C local search."""

    enabled: bool
    iterations_executed: int
    moves_evaluated: int
    moves_accepted: int
    runtime_seconds: float
    termination_reason: TerminationReason
    improved: bool
    initial_assigned_count: int
    final_assigned_count: int
    assigned_count_delta: int
    initial_travel_min: int
    final_travel_min: int
    travel_min_delta: int
    initial_weighted_cost: float
    final_weighted_cost: float
    weighted_cost_delta: float
    initial_mean_soft_sla_urgency: float
    final_mean_soft_sla_urgency: float
    changes: list[OptimizationChangeRecord] = Field(default_factory=list)


class JobAuditEntry(BaseModel):
    """Per-job feasibility diagnostic in the dataset audit."""

    job_id: str
    priority: str
    zone: str
    required_skills: list[str]
    skill_eligible_count: int
    zone_eligible_count: int
    static_eligible_count: int
    isolated_feasible_electrician_count: int
    isolated_feasible_slot_count: int
    infeasible_reasons: list[str] = Field(default_factory=list)


class DatasetAuditReport(BaseModel):
    """Comprehensive mandatory dataset feasibility audit (Section 3)."""

    total_electricians: int
    active_electricians: int
    total_jobs: int
    distinct_skills_electricians: list[str]
    distinct_skills_jobs: list[str]
    unmatched_job_skills: list[str]
    distinct_certifications_electricians: list[str]
    distinct_zones_electricians: list[str]
    distinct_zones_jobs: list[str]
    unserved_job_zones: list[str]
    distinct_shifts: list[str]
    priority_distribution: dict[str, int]
    skill_eligibility_buckets: dict[str, int]
    zone_eligibility_buckets: dict[str, int]
    static_eligibility_buckets: dict[str, int]
    isolated_feasibility_buckets_hard_sla: dict[str, int]
    isolated_feasibility_buckets_soft_sla: dict[str, int]
    isolated_infeasible_jobs_hard_sla: list[JobAuditEntry]
    isolated_infeasible_jobs_soft_sla: list[JobAuditEntry]
    jobs_with_multiple_feasible_alternatives_hard_sla: int
    jobs_with_single_static_electrician: list[str]
    travel_matrix_row_count: int
    expected_baseline_location_count: int
    missing_baseline_travel_pairs: list[str]
    scenario_locations_missing_from_matrix: list[str]
    invalid_travel_entries: list[str]
    malformed_records: list[str]
    post_schedule_assigned_count: int | None = None
    post_schedule_unassigned_count: int | None = None
    post_schedule_unassigned_by_reason: dict[str, int] | None = None
    supports_tradeoffs: dict[str, bool]
    tradeoff_assessment: list[str]
    dataset_limitations: list[str]
    proposed_minimal_improvements: list[str]


class ScheduleRunResult(BaseModel):
    """Top-level structured result returned by the scheduling engine and FastAPI."""

    run_id: str
    created_at_utc: datetime
    active_scenario_ids: list[str] = Field(default_factory=list)
    config: SchedulerConfig
    initial_greedy_schedule: ScheduleSnapshot
    final_schedule: ScheduleSnapshot
    optimization: OptimizationSummary
    assigned_job_ids: list[str]
    unassigned_job_ids: list[str]
    explanations: dict[str, AssignmentExplanation]
    unassigned_reasons: dict[str, UnassignedJobReport]
    validation_warnings: list[str] = Field(default_factory=list)
    is_valid_for_commitment: bool
    dataset_audit: DatasetAuditReport | None = None


# ---------------------------------------------------------------------------
# FastAPI Request & Response Schemas
# ---------------------------------------------------------------------------


class GenerateScheduleRequest(BaseModel):
    """Request payload to generate (and optionally optimize) a schedule."""

    model_config = ConfigDict(extra="forbid")

    run_id: str | None = None
    use_bundled_dataset: bool = Field(
        default=True,
        description="When True and jobs/electricians are omitted, load from bundled data/ CSVs.",
    )
    scenario_ids: list[str] = Field(
        default_factory=list,
        description="Optional disruption scenario IDs (e.g. ['D01'], ['D02']) to load scenario inputs.",
    )
    electricians: list[Electrician] | None = None
    jobs: list[Job] | None = None
    travel_times: list[TravelEntry] | None = None
    unavailability: list[UnavailabilityInterval] | None = None
    existing_assignments: list[ExistingAssignment] = Field(default_factory=list)
    include_dataset_audit: bool = Field(default=False)
    config: SchedulerConfig = Field(default_factory=SchedulerConfig)


class OptimizeScheduleRequest(BaseModel):
    """Request payload to run or re-run bounded local search optimization."""

    model_config = ConfigDict(extra="forbid")

    run_id: str | None = Field(
        default=None,
        description="Existing run_id to re-optimize, or None to generate and optimize from payload/dataset.",
    )
    use_bundled_dataset: bool = Field(default=False)
    scenario_ids: list[str] = Field(default_factory=list)
    electricians: list[Electrician] | None = None
    jobs: list[Job] | None = None
    travel_times: list[TravelEntry] | None = None
    unavailability: list[UnavailabilityInterval] | None = None
    existing_assignments: list[ExistingAssignment] = Field(default_factory=list)
    config_overrides: SchedulerConfig | None = None


class ScheduleMetricsResponse(BaseModel):
    """Focused metrics comparison view for an executed schedule run."""

    run_id: str
    created_at_utc: datetime
    is_valid_for_commitment: bool
    assigned_count: int
    unassigned_count: int
    high_priority_unassigned_count: int
    total_travel_min: int
    total_service_min: int
    hard_constraint_violation_count: int
    hard_sla_violation_count: int
    predicted_soft_sla_breach_count: int
    mean_soft_sla_urgency: float
    max_soft_sla_urgency: float
    initial_objective: ObjectiveBreakdown
    final_objective: ObjectiveBreakdown
    technician_workloads: list[TechnicianWorkloadSummary]
    optimization: OptimizationSummary
    validation_warnings: list[str]


class ScheduleExplanationsResponse(BaseModel):
    """Assignment explanations and unassigned job diagnostics for a run."""

    run_id: str
    created_at_utc: datetime
    assigned_explanations: dict[str, AssignmentExplanation]
    unassigned_reasons: dict[str, UnassignedJobReport]


class ErrorResponse(BaseModel):
    """Consistent structured API error response."""

    error_code: str
    message: str
    details: list[str] = Field(default_factory=list)
