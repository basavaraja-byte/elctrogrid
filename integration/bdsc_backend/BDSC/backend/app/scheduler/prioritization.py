"""Priority, soft-deadline urgency, and resource scarcity policies (Section 7).

Ordering policy hierarchy:
1. Hard constraints and fixed commitments are enforced prior to ordering.
2. Business priority strictly partitions jobs:
   Critical (rank 1) > High (rank 2) > Normal/Medium (rank 3) > Low (rank 4).
   Lower-priority work can NEVER outrank higher-priority work.
3. Within a business-priority tier, higher soft-deadline urgency comes first:
   urgency = 100 * (1 - clamp(slack_minutes / H, 0, 1)), default H = 240 min.
4. Resource scarcity breaks ties in favor of more constrained jobs
   (fewer feasible electricians, fewer feasible slots, fewer static electricians).
5. Lexicographical job_id provides a 100% deterministic final tie-breaker.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.scheduler.constraints import ResolvedJob
from app.schemas.scheduling import PriorityLevel


def clamp(value: float, low: float, high: float) -> float:
    """Clamp a numeric value to [low, high]."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def compute_soft_sla_urgency(slack_minutes: float, horizon_min: float = 240.0) -> float:
    """Compute heuristic soft-deadline urgency in [0.0, 100.0].

    Formula:
        urgency = 100 * (1 - clamp(slack_minutes / H, 0, 1))

    Assumptions:
    - slack_minutes = sla_deadline_min - completion_min.
    - Slack >= H yields 0 urgency; slack == 0 yields 100 urgency.
    - Negative slack makes a candidate infeasible when the deadline is hard;
      when soft deadlines are enabled, negative slack clamps to 100 urgency.
    - Configurable heuristic parameter H defaults to 240 minutes.
    """
    if horizon_min <= 0:
        raise ValueError(f"horizon_min must be positive, got {horizon_min}")
    ratio = clamp(slack_minutes / horizon_min, 0.0, 1.0)
    return round(100.0 * (1.0 - ratio), 6)


def classify_deadline_risk(
    slack_min: int,
    horizon_min: float = 240.0,
) -> Literal["low", "moderate", "high", "critical_zero_slack", "soft_breach"]:
    """Categorize predicted deadline margin into human-readable risk bands."""
    if slack_min < 0:
        return "soft_breach"
    if slack_min == 0:
        return "critical_zero_slack"
    if slack_min <= 60:
        return "high"
    if slack_min < horizon_min:
        return "moderate"
    return "low"


@dataclass(frozen=True, slots=True)
class JobPriorityProfile:
    """Computed priority, urgency, and scarcity metrics for ordering a job."""

    job_id: str
    priority: PriorityLevel
    priority_rank: int
    eligible_electrician_count: int
    feasible_electrician_count: int
    feasible_slot_count: int
    best_slack_min: int | None
    urgency_score: float
    scarcity_index: float

    def ordering_key(self) -> tuple[int, float, int, int, int, str]:
        """Deterministic tuple sort key implementing Section 7's 5-step policy."""
        return (
            self.priority_rank,
            -round(self.urgency_score, 6),
            self.feasible_electrician_count,
            self.feasible_slot_count,
            self.eligible_electrician_count,
            self.job_id,
        )


def build_job_priority_profile(
    job: ResolvedJob,
    eligible_electrician_count: int,
    feasible_electrician_count: int,
    feasible_slot_count: int,
    best_slack_min: int | None,
    horizon_min: float = 240.0,
) -> JobPriorityProfile:
    """Construct a JobPriorityProfile from static and dynamic candidate counts."""
    if best_slack_min is not None:
        urgency = compute_soft_sla_urgency(best_slack_min, horizon_min)
    else:
        # Fallback estimate from intrinsic job window + duration when no slot is feasible
        intrinsic_slack = job.sla_deadline_min - (job.window_start_min + job.duration_min)
        urgency = compute_soft_sla_urgency(intrinsic_slack, horizon_min)

    # Scarcity index in (0.0, 1.0]: 1.0 when <=1 feasible electrician, smaller when many options exist
    denom = max(1, feasible_electrician_count) if feasible_electrician_count > 0 else 1
    scarcity_index = round(1.0 / denom, 6)

    return JobPriorityProfile(
        job_id=job.job_id,
        priority=job.priority,
        priority_rank=job.priority.rank,
        eligible_electrician_count=eligible_electrician_count,
        feasible_electrician_count=feasible_electrician_count,
        feasible_slot_count=feasible_slot_count,
        best_slack_min=best_slack_min,
        urgency_score=urgency,
        scarcity_index=scarcity_index,
    )


def sort_jobs_by_policy(profiles: list[JobPriorityProfile]) -> list[JobPriorityProfile]:
    """Return profiles ordered strictly by the documented priority/urgency/scarcity policy."""
    return sorted(profiles, key=lambda p: p.ordering_key())


def compute_technician_scarcity_pressure(
    unassigned_jobs: list[ResolvedJob],
    eligible_techs_by_job: dict[str, list[str]],
) -> dict[str, float]:
    """Measure how strongly remaining unassigned jobs depend on each technician.

    If a remaining job has only 1 eligible technician T, T receives +1.0 bottleneck weight;
    if 2 eligible technicians, each receives +0.5; if k <= 3, +1/k. Flexible jobs with
    many alternatives use this signal to avoid unnecessarily consuming scarce specialists.
    """
    pressure: dict[str, float] = {}
    for job in unassigned_jobs:
        tech_ids = eligible_techs_by_job.get(job.job_id, [])
        count = len(tech_ids)
        if 1 <= count <= 3:
            weight = (1.5 if job.priority.is_high_or_critical else 1.0) / float(count)
            for tid in tech_ids:
                pressure[tid] = pressure.get(tid, 0.0) + weight
    return pressure

