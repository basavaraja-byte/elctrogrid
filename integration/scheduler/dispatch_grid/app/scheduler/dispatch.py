"""Technician Assignment Dispatch, 5-Minute Timeout, Acceptance/Rejection, and Retry Engine.

Extends DispatchGrid Modules B & C without altering core constraint or optimization logic:
- Issues versioned assignment offers with a configurable response timeout (default 300s = 5 min).
- Supports technician acceptance and rejection.
- Automatically attempts the next eligible & feasible technician on rejection or timeout,
  reusing Module B (`generate_candidates_for_job`, `validate_full_schedule`) and Module C
  (`score_greedy_candidate`, `evaluate_schedule_objective`).
- Prevents duplicate assignments, stale/expired responses, technician mismatches, and
  conflicting concurrent assignment attempts via re-entrant locking and offer-state guards.
- Transitions cleanly to `EXHAUSTED_UNASSIGNED` with grounded diagnostics when no eligible
  and feasible technician remains.
"""

from __future__ import annotations

import threading
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

from app.scheduler.candidates import (
    CandidateEvaluationResult,
    InsertionCandidate,
    generate_candidates_for_job,
    get_static_eligible_electricians,
    stop_to_spec,
    build_timed_route,
)
from app.scheduler.constraints import (
    ConstraintFailure,
    ResolvedJob,
    RouteStop,
    is_historical_or_active_commitment,
    validate_full_schedule,
    validate_job_data,
)
from app.scheduler.explanations import (
    build_assignment_explanation,
    build_invalid_job_report,
    build_unassigned_job_report,
    compute_incremental_travel_for_stop,
)
from app.scheduler.objective import (
    compute_technician_workloads,
    evaluate_schedule_objective,
    score_greedy_candidate,
)
from app.scheduler.prioritization import (
    compute_soft_sla_urgency,
    compute_technician_scarcity_pressure,
)
from app.scheduler.travel import TravelMatrix
from app.schemas.dispatch_recovery import (
    AssignmentOffer,
    DispatchActionResponse,
    DispatchConfig,
    DispatchStateSnapshot,
    DispatchTransitionEvent,
    JobDispatchRecord,
    JobDispatchStatus,
    OfferStatus,
    RejectedCandidateSummary,
)
from app.schemas.scheduling import (
    Electrician,
    ExistingAssignment,
    Job,
    JobStatus,
    ReasonCode,
    ScheduledAssignment,
    ScheduleRunResult,
    SchedulerConfig,
    ScheduleSnapshot,
    TravelEntry,
    UnassignedJobReport,
    UnavailabilityInterval,
    minutes_to_hhmm,
    minutes_to_utc_datetime,
)


class DispatchError(Exception):
    """Base exception for assignment dispatch protocol violations."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class OfferNotFoundError(DispatchError):
    """Raised when an offer_id or job_id does not exist in the dispatch session."""

    def __init__(self, message: str) -> None:
        super().__init__("OFFER_NOT_FOUND", message)


class StaleOfferError(DispatchError):
    """Raised when a technician responds to an expired, timed-out, rejected, or superseded offer."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(error_code, message)


class DispatchConflictError(DispatchError):
    """Raised on duplicate offer creation, wrong technician, or already-finalized offer."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(error_code, message)


def _normalize_utc(dt: datetime | None) -> datetime:
    """Return timezone-aware UTC datetime, rejecting naive datetimes."""
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise DispatchError(
            "INVALID_TIMESTAMP",
            "Dispatch timestamps must be timezone-aware UTC datetimes.",
        )
    return dt.astimezone(timezone.utc)


def _extract_rejected_summaries(
    eval_res: CandidateEvaluationResult,
    excluded_techs: list[str],
    previous_offers: list[AssignmentOffer],
    limit: int = 10,
) -> list[RejectedCandidateSummary]:
    """Summarize prior declined/timed-out attempts plus Module B candidate rejections."""
    summaries: list[RejectedCandidateSummary] = []
    seen_keys: set[tuple[str, str]] = set()

    for prev in previous_offers:
        if prev.status in (OfferStatus.REJECTED, OfferStatus.TIMED_OUT):
            detail = (
                f"Attempt #{prev.attempt_number} on {prev.technician_id} {prev.status.value}"
                + (f" ({prev.response_reason})" if prev.response_reason else "")
            )
            key = (prev.technician_id, prev.status.value)
            if key not in seen_keys:
                seen_keys.add(key)
                summaries.append(
                    RejectedCandidateSummary(
                        technician_id=prev.technician_id,
                        reason_code=ReasonCode.NO_AVAILABLE_SLOT,
                        detail=detail,
                    )
                )

    for failure in eval_res.rejection_details:
        # Extract technician_id if mentioned in detail, else 'fleet'
        tech_hint = "fleet"
        for token in failure.detail.replace("'", " ").replace(":", " ").split():
            if token.startswith("E") and len(token) >= 2 and token[1:].isdigit():
                tech_hint = token
                break
        key = (tech_hint, failure.code.value)
        if key not in seen_keys:
            seen_keys.add(key)
            summaries.append(
                RejectedCandidateSummary(
                    technician_id=tech_hint,
                    reason_code=failure.code,
                    detail=failure.detail,
                )
            )
        if len(summaries) >= limit:
            break

    return summaries


class DispatchSession:
    """Concurrency-safe technician offer, 5-minute timeout, and next-eligible retry coordinator."""

    def __init__(
        self,
        schedule_result: ScheduleRunResult,
        jobs: list[Job],
        electricians: list[Electrician],
        travel_times: list[TravelEntry] | TravelMatrix,
        unavailability: list[UnavailabilityInterval] | None = None,
        existing_assignments: list[ExistingAssignment] | None = None,
        dispatch_config: DispatchConfig | None = None,
        now_utc: datetime | None = None,
        auto_offer_all: bool = False,
    ) -> None:
        self._lock = threading.RLock()
        self.run_id = schedule_result.run_id
        self.scheduler_config: SchedulerConfig = schedule_result.config
        self.dispatch_config: DispatchConfig = dispatch_config or DispatchConfig()
        self.created_at_utc = _normalize_utc(now_utc)
        self.last_updated_utc = self.created_at_utc

        self._electricians = sorted(electricians, key=lambda e: e.technician_id)
        self._elecs_by_id: dict[str, Electrician] = {
            e.technician_id: e for e in self._electricians
        }
        self._existing_assignments: list[ExistingAssignment] = list(existing_assignments or [])
        self._unavail_list: list[UnavailabilityInterval] = list(unavailability or [])
        self._unavail_by_tech: dict[str, list[UnavailabilityInterval]] = {}
        for u in self._unavail_list:
            self._unavail_by_tech.setdefault(u.technician_id, []).append(u)
        for tid in self._unavail_by_tech:
            self._unavail_by_tech[tid].sort(key=lambda x: (x.start_min, x.end_min, x.unavailability_id))

        if isinstance(travel_times, TravelMatrix):
            self._travel_matrix = travel_times
        else:
            self._travel_matrix = TravelMatrix(
                entries=travel_times,
                electricians=self._electricians,
                jobs=jobs,
                allow_coordinate_fallback=self.scheduler_config.allow_coordinate_travel_fallback,
            )

        cancelled_ids = {
            ex.job_id
            for ex in self._existing_assignments
            if ex.status.strip().lower() == JobStatus.CANCELLED.value
        }
        self._active_jobs_by_id: dict[str, ResolvedJob] = {}
        self._invalid_job_reports: dict[str, UnassignedJobReport] = {}
        for job in jobs:
            if job.job_id in cancelled_ids or job.status.strip().lower() == JobStatus.CANCELLED.value:
                cancelled_ids.add(job.job_id)
                continue
            if job.job_id in self._active_jobs_by_id or job.job_id in self._invalid_job_reports:
                continue
            rjob, errs = validate_job_data(job, self.scheduler_config)
            if rjob is None:
                self._invalid_job_reports[job.job_id] = build_invalid_job_report(
                    job.job_id, job.priority, errs
                )
            else:
                self._active_jobs_by_id[job.job_id] = rjob

        # Precompute isolated evaluations & static eligibility for grounded diagnostics
        empty_routes: dict[str, list[RouteStop]] = {e.technician_id: [] for e in self._electricians}
        self._isolated_evals: dict[str, CandidateEvaluationResult] = {}
        self._static_eligible_map: dict[str, list[str]] = {}
        for jid, rjob in sorted(self._active_jobs_by_id.items()):
            iso = generate_candidates_for_job(
                job=rjob,
                electricians=self._electricians,
                routes_by_tech=empty_routes,
                unavailability_by_tech=self._unavail_by_tech,
                travel_matrix=self._travel_matrix,
                config=self.scheduler_config,
            )
            self._isolated_evals[jid] = iso
            self._static_eligible_map[jid] = iso.static_eligible_ids

        # Reconstruct live routes from schedule_result.final_schedule
        self._routes_by_tech: dict[str, list[RouteStop]] = {
            e.technician_id: [] for e in self._electricians
        }
        existing_prot_lookup: dict[str, ExistingAssignment] = {}
        for ex in self._existing_assignments:
            st = ex.status.strip().lower()
            if ex.locked or st == JobStatus.COMPLETED.value or (
                self.scheduler_config.protect_in_progress and st == JobStatus.IN_PROGRESS.value
            ):
                existing_prot_lookup[ex.job_id] = ex

        self._job_records: dict[str, JobDispatchRecord] = {}
        self._offers_by_id: dict[str, AssignmentOffer] = {}
        self._events: list[DispatchTransitionEvent] = []

        for asgn in schedule_result.final_schedule.assignments:
            rjob = self._active_jobs_by_id.get(asgn.job_id)
            if rjob is None:
                continue
            ex_prot = existing_prot_lookup.get(asgn.job_id)
            is_hist = is_historical_or_active_commitment(
                asgn.status, asgn.is_protected, self.scheduler_config
            )
            stop = RouteStop(
                job=rjob,
                technician_id=asgn.technician_id,
                from_location_id=asgn.from_location_id,
                departure_min=asgn.departure_min,
                arrival_min=asgn.arrival_min,
                planned_start_min=asgn.planned_start_min,
                completion_min=asgn.completion_min,
                travel_time_min=asgn.travel_time_min,
                travel_source=asgn.travel_estimate_source,
                status=asgn.status,
                is_protected=asgn.is_protected,
                locked_departure_min=(
                    asgn.departure_min
                    if is_hist
                    else (ex_prot.departure_min if ex_prot else None)
                ),
                locked_arrival_min=(
                    asgn.arrival_min
                    if is_hist
                    else (ex_prot.arrival_min if ex_prot else None)
                ),
                locked_completion_min=(
                    asgn.completion_min
                    if asgn.status.strip().lower() == JobStatus.COMPLETED.value
                    else None
                ),
                locked_origin_id=asgn.from_location_id if asgn.is_protected else None,
            )
            self._routes_by_tech[asgn.technician_id].append(stop)

            if asgn.is_protected:
                self._job_records[asgn.job_id] = JobDispatchRecord(
                    job_id=asgn.job_id,
                    priority=rjob.priority,
                    dispatch_status=JobDispatchStatus.LOCKED_COMMITTED,
                    assigned_technician_id=asgn.technician_id,
                    planned_start_min=asgn.planned_start_min,
                    planned_completion_min=asgn.completion_min,
                )
            else:
                self._job_records[asgn.job_id] = JobDispatchRecord(
                    job_id=asgn.job_id,
                    priority=rjob.priority,
                    dispatch_status=JobDispatchStatus.PLANNED_UNOFFERED,
                    assigned_technician_id=asgn.technician_id,
                    planned_start_min=asgn.planned_start_min,
                    planned_completion_min=asgn.completion_min,
                )

        # Register jobs that were already unassigned in initial schedule
        unassigned_map = {r.job_id: r for r in schedule_result.final_schedule.unassigned_reports}
        for jid, rjob in sorted(self._active_jobs_by_id.items()):
            if jid not in self._job_records:
                self._job_records[jid] = JobDispatchRecord(
                    job_id=jid,
                    priority=rjob.priority,
                    dispatch_status=JobDispatchStatus.EXHAUSTED_UNASSIGNED,
                    final_unassigned_reason=unassigned_map.get(jid),
                )

        if auto_offer_all:
            self.offer_all_pending(now_utc=self.created_at_utc)

    def _record_event(
        self,
        timestamp_utc: datetime,
        job_id: str,
        event_type: str,
        summary: str,
        offer_id: str | None = None,
        technician_id: str | None = None,
        attempt_number: int | None = None,
        next_offer_id: str | None = None,
        next_technician_id: str | None = None,
    ) -> None:
        self._events.append(
            DispatchTransitionEvent(
                event_id=f"evt-{uuid.uuid4().hex[:10]}",
                timestamp_utc=timestamp_utc,
                job_id=job_id,
                event_type=event_type,  # type: ignore[arg-type]
                offer_id=offer_id,
                technician_id=technician_id,
                attempt_number=attempt_number,
                next_offer_id=next_offer_id,
                next_technician_id=next_technician_id,
                summary=summary,
            )
        )

    def _find_stop(self, job_id: str) -> tuple[str, int, RouteStop] | None:
        for tid, route in self._routes_by_tech.items():
            for idx, stop in enumerate(route):
                if stop.job.job_id == job_id:
                    return tid, idx, stop
        return None

    def _remove_job_from_route(self, job_id: str) -> None:
        located = self._find_stop(job_id)
        if located is None:
            return
        tid, idx, _ = located
        elec = self._elecs_by_id[tid]
        cur_route = self._routes_by_tech[tid]
        rem_stops = cur_route[:idx] + cur_route[idx + 1:]
        if not rem_stops:
            self._routes_by_tech[tid] = []
            return
        rem_specs = [stop_to_spec(s) for s in rem_stops]
        retimed, _ = build_timed_route(
            electrician=elec,
            specs=rem_specs,
            unavailability=self._unavail_by_tech.get(tid, []),
            travel_matrix=self._travel_matrix,
            config=self.scheduler_config,
        )
        if retimed is not None:
            self._routes_by_tech[tid] = retimed
        else:
            self._routes_by_tech[tid] = rem_stops

    def _effective_existing_commitments(self) -> list[ExistingAssignment]:
        """Build ExistingAssignment list combining input protected stops, ACCEPTED stops, and active PENDING_RESPONSE offers."""
        commitments = list(self._existing_assignments)
        known_prot = {
            ex.job_id
            for ex in commitments
            if ex.is_protected
        }
        for jid, rec in self._job_records.items():
            is_active_dispatch_lock = (
                rec.dispatch_status == JobDispatchStatus.ACCEPTED
                or (
                    rec.dispatch_status == JobDispatchStatus.PENDING_RESPONSE
                    and rec.active_offer_id is not None
                )
            )
            if (
                is_active_dispatch_lock
                and jid not in known_prot
                and rec.assigned_technician_id is not None
                and rec.planned_start_min is not None
            ):
                located = self._find_stop(jid)
                stop_status = located[2].status if located is not None else JobStatus.ASSIGNED.value
                commitments.append(
                    ExistingAssignment(
                        job_id=jid,
                        technician_id=rec.assigned_technician_id,
                        planned_start_min=rec.planned_start_min,
                        completion_min=rec.planned_completion_min,
                        status=stop_status,
                        locked=True,
                    )
                )
        return commitments

    def _create_offer_for_stop(
        self,
        job_id: str,
        tid: str,
        pos: int,
        stop: RouteStop,
        now_utc: datetime,
        eval_res: CandidateEvaluationResult | None = None,
    ) -> AssignmentOffer:
        rec = self._job_records[job_id]
        elec = self._elecs_by_id[tid]
        route = self._routes_by_tech[tid]

        # Pin the offered stop as protected while PENDING_RESPONSE so concurrent offers cannot
        # displace or overlap it while the technician decides.
        stop.is_protected = True
        stop.locked_origin_id = stop.from_location_id

        skip_travel: int | None = None
        if pos + 1 < len(route):
            skip_res = self._travel_matrix.lookup(stop.from_location_id, route[pos + 1].job.location_id)
            skip_travel = skip_res.travel_time_min if skip_res is not None else None
        inc_travel = compute_incremental_travel_for_stop(route, pos, skip_travel)

        if eval_res is None:
            elig_e, _ = get_static_eligible_electricians(stop.job, self._electricians)
            eval_res = CandidateEvaluationResult(
                job=stop.job,
                static_eligible_ids=[e.technician_id for e in elig_e],
            )

        expl = build_assignment_explanation(
            stop=stop,
            route_position=pos,
            route_length=len(route),
            incremental_travel_min=inc_travel,
            electrician=elec,
            greedy_eval=eval_res,
            config=self.scheduler_config,
        )
        rejected_alts = _extract_rejected_summaries(
            eval_res=eval_res,
            excluded_techs=rec.excluded_technician_ids,
            previous_offers=rec.offers,
        )

        attempt = rec.attempts_made + 1
        offer_id = f"off-{self.run_id}-{job_id}-{attempt}"
        expires_at = now_utc + timedelta(seconds=self.dispatch_config.response_timeout_seconds)

        offer = AssignmentOffer(
            offer_id=offer_id,
            run_id=self.run_id,
            job_id=job_id,
            technician_id=tid,
            attempt_number=attempt,
            status=OfferStatus.PENDING_RESPONSE,
            route_position=pos,
            from_location_id=stop.from_location_id,
            planned_departure_min=stop.departure_min,
            planned_arrival_min=stop.arrival_min,
            planned_start_min=stop.planned_start_min,
            planned_completion_min=stop.completion_min,
            travel_time_min=stop.travel_time_min,
            offered_at_utc=now_utc,
            expires_at_utc=expires_at,
            selection_explanation=expl,
            rejected_alternatives=rejected_alts,
        )

        rec.attempts_made = attempt
        rec.dispatch_status = JobDispatchStatus.PENDING_RESPONSE
        rec.assigned_technician_id = tid
        rec.planned_start_min = stop.planned_start_min
        rec.planned_completion_min = stop.completion_min
        rec.active_offer_id = offer_id
        rec.final_unassigned_reason = None
        rec.offers.append(offer)
        self._offers_by_id[offer_id] = offer
        return offer

    def _build_exhausted_report(
        self,
        rjob: ResolvedJob,
        rec: JobDispatchRecord,
        eval_res: CandidateEvaluationResult,
    ) -> UnassignedJobReport:
        """Build an actionable UnassignedJobReport when all eligible technicians rejected/timed out or lacked slots."""
        prior_notes = [
            f"Attempt #{o.attempt_number} ({o.technician_id}): {o.status.value}"
            + (f" — {o.response_reason}" if o.response_reason else "")
            for o in rec.offers
        ]
        remaining_elecs = [
            e for e in self._electricians if e.technician_id not in set(rec.excluded_technician_ids)
        ]

        if not eval_res.static_eligible_ids:
            # Determine whether the roster originally had eligible electricians who rejected/timed out
            orig_static = self._static_eligible_map.get(rjob.job_id, [])
            if orig_static:
                details = prior_notes + [
                    f"All {len(orig_static)} statically eligible electrician(s) ({', '.join(orig_static)}) "
                    f"rejected or timed out on {rjob.job_id}; zero eligible backups remain."
                ]
                return UnassignedJobReport(
                    job_id=rjob.job_id,
                    priority=rjob.priority.value,
                    primary_reason_code=ReasonCode.NO_AVAILABLE_SLOT,
                    summary=(
                        f"No eligible technician remains for job {rjob.job_id} after {len(rec.offers)} "
                        f"dispatch attempt(s) across {', '.join(rec.excluded_technician_ids)}."
                    ),
                    is_statically_eligible=True,
                    static_eligible_count=len(orig_static),
                    static_eligible_technician_ids=list(orig_static),
                    isolated_feasible_count=0,
                    rejection_counts_by_code={ReasonCode.NO_AVAILABLE_SLOT.value: len(rec.offers)},
                    supporting_details=details,
                )

            base_rep = build_unassigned_job_report(
                job=rjob,
                final_eval=eval_res,
                isolated_eval=self._isolated_evals[rjob.job_id],
                all_electricians=remaining_elecs,
            )
            return base_rep

        # Remaining statically eligible technicians exist, but none had a feasible time slot
        base_rep = build_unassigned_job_report(
            job=rjob,
            final_eval=eval_res,
            isolated_eval=self._isolated_evals[rjob.job_id],
            all_electricians=remaining_elecs,
        )
        merged_details = prior_notes + list(base_rep.supporting_details)
        summary_prefix = (
            f"After {len(rec.offers)} rejected/timed-out attempt(s) ({', '.join(rec.excluded_technician_ids)}), "
            if rec.offers
            else ""
        )
        return base_rep.model_copy(
            update={
                "summary": summary_prefix + base_rep.summary,
                "supporting_details": merged_details[:12],
            }
        )

    def _attempt_next_eligible_technician(
        self,
        job_id: str,
        now_utc: datetime,
        trigger_label: str,
    ) -> AssignmentOffer | None:
        """Find the best valid next technician/slot for job_id, or mark EXHAUSTED_UNASSIGNED."""
        rjob = self._active_jobs_by_id[job_id]
        rec = self._job_records[job_id]
        excluded_set = set(rec.excluded_technician_ids)
        candidate_elecs = [
            e for e in self._electricians if e.technician_id not in excluded_set
        ]

        eval_res = generate_candidates_for_job(
            job=rjob,
            electricians=candidate_elecs,
            routes_by_tech=self._routes_by_tech,
            unavailability_by_tech=self._unavail_by_tech,
            travel_matrix=self._travel_matrix,
            config=self.scheduler_config,
        )

        if eval_res.candidates:
            unassigned_now = [
                self._active_jobs_by_id[jid]
                for jid, r in self._job_records.items()
                if r.dispatch_status == JobDispatchStatus.EXHAUSTED_UNASSIGNED and jid != job_id
            ]
            pressure = compute_technician_scarcity_pressure(unassigned_now, self._static_eligible_map)
            ranked: list[InsertionCandidate] = sorted(
                eval_res.candidates,
                key=lambda c: score_greedy_candidate(
                    c,
                    self.scheduler_config,
                    pressure,
                    eval_res.feasible_electrician_count,
                ),
            )

            eff_existing = self._effective_existing_commitments()
            for cand in ranked:
                trial_routes = dict(self._routes_by_tech)
                trial_routes[cand.technician_id] = [s.clone() for s in cand.updated_route]
                val = validate_full_schedule(
                    routes_by_tech=trial_routes,
                    electricians_by_id=self._elecs_by_id,
                    valid_jobs_by_id=self._active_jobs_by_id,
                    unavailability_by_tech=self._unavail_by_tech,
                    existing_assignments=eff_existing,
                    travel_matrix=self._travel_matrix,
                    config=self.scheduler_config,
                )
                if not val.is_valid:
                    continue

                # Commit new route and synchronize any shifted PLANNED_UNOFFERED stop metadata
                self._routes_by_tech[cand.technician_id] = trial_routes[cand.technician_id]
                for s in self._routes_by_tech[cand.technician_id]:
                    s_rec = self._job_records.get(s.job.job_id)
                    if s_rec and s_rec.dispatch_status == JobDispatchStatus.PLANNED_UNOFFERED:
                        s_rec.planned_start_min = s.planned_start_min
                        s_rec.planned_completion_min = s.completion_min

                inserted_stop = self._routes_by_tech[cand.technician_id][cand.insert_position]
                new_offer = self._create_offer_for_stop(
                    job_id=job_id,
                    tid=cand.technician_id,
                    pos=cand.insert_position,
                    stop=inserted_stop,
                    now_utc=now_utc,
                    eval_res=eval_res,
                )
                self._record_event(
                    timestamp_utc=now_utc,
                    job_id=job_id,
                    event_type="retry_offer_issued" if rec.attempts_made > 1 else "offer_issued",
                    offer_id=new_offer.offer_id,
                    technician_id=new_offer.technician_id,
                    attempt_number=new_offer.attempt_number,
                    summary=(
                        f"{trigger_label}: issued offer {new_offer.offer_id} (attempt #{new_offer.attempt_number}) "
                        f"to {new_offer.technician_id} starting at {minutes_to_hhmm(new_offer.planned_start_min)} "
                        f"(expires {new_offer.expires_at_utc.isoformat()})."
                    ),
                )
                return new_offer

        # Zero valid candidates remain -> mark EXHAUSTED_UNASSIGNED
        exhausted_report = self._build_exhausted_report(rjob, rec, eval_res)
        rec.dispatch_status = JobDispatchStatus.EXHAUSTED_UNASSIGNED
        rec.assigned_technician_id = None
        rec.planned_start_min = None
        rec.planned_completion_min = None
        rec.active_offer_id = None
        rec.final_unassigned_reason = exhausted_report
        self._record_event(
            timestamp_utc=now_utc,
            job_id=job_id,
            event_type="candidates_exhausted",
            attempt_number=rec.attempts_made,
            summary=exhausted_report.summary,
        )
        return None

    def offer_job(
        self,
        job_id: str,
        now_utc: datetime | None = None,
    ) -> AssignmentOffer | None:
        """Issue an assignment offer for `job_id`, preventing duplicate or conflicting offers."""
        with self._lock:
            ts = _normalize_utc(now_utc)
            self.last_updated_utc = ts

            if job_id not in self._job_records:
                raise OfferNotFoundError(f"Job '{job_id}' is not part of schedule run '{self.run_id}'.")

            rec = self._job_records[job_id]
            if rec.dispatch_status in (JobDispatchStatus.ACCEPTED, JobDispatchStatus.LOCKED_COMMITTED):
                self._record_event(
                    timestamp_utc=ts,
                    job_id=job_id,
                    event_type="stale_or_conflicting_attempt_blocked",
                    technician_id=rec.assigned_technician_id,
                    summary=f"Blocked duplicate dispatch request for already committed job {job_id}.",
                )
                raise DispatchConflictError(
                    "JOB_ALREADY_ASSIGNED",
                    f"Job '{job_id}' is already committed to technician '{rec.assigned_technician_id}'.",
                )

            if rec.dispatch_status == JobDispatchStatus.PENDING_RESPONSE and rec.active_offer_id is not None:
                active_off = self._offers_by_id[rec.active_offer_id]
                if ts < active_off.expires_at_utc:
                    self._record_event(
                        timestamp_utc=ts,
                        job_id=job_id,
                        event_type="stale_or_conflicting_attempt_blocked",
                        offer_id=active_off.offer_id,
                        technician_id=active_off.technician_id,
                        attempt_number=active_off.attempt_number,
                        summary=(
                            f"Blocked concurrent dispatch attempt for {job_id}; active offer "
                            f"{active_off.offer_id} on {active_off.technician_id} is still pending response."
                        ),
                    )
                    raise DispatchConflictError(
                        "CONCURRENT_DISPATCH_CONFLICT",
                        f"Job '{job_id}' already has pending offer '{active_off.offer_id}' on '{active_off.technician_id}'.",
                    )
                # Active offer already expired -> expire it before proceeding
                self._expire_single_offer(active_off, ts, auto_retry=False)

            if rec.dispatch_status == JobDispatchStatus.PLANNED_UNOFFERED:
                located = self._find_stop(job_id)
                if located is not None:
                    tid, pos, stop = located
                    # Verify full schedule validity before issuing initial offer
                    val = validate_full_schedule(
                        routes_by_tech=self._routes_by_tech,
                        electricians_by_id=self._elecs_by_id,
                        valid_jobs_by_id=self._active_jobs_by_id,
                        unavailability_by_tech=self._unavail_by_tech,
                        existing_assignments=self._effective_existing_commitments(),
                        travel_matrix=self._travel_matrix,
                        config=self.scheduler_config,
                    )
                    if val.is_valid:
                        offer = self._create_offer_for_stop(job_id, tid, pos, stop, ts)
                        self._record_event(
                            timestamp_utc=ts,
                            job_id=job_id,
                            event_type="offer_issued",
                            offer_id=offer.offer_id,
                            technician_id=offer.technician_id,
                            attempt_number=offer.attempt_number,
                            summary=(
                                f"Issued initial offer {offer.offer_id} to {offer.technician_id} "
                                f"for {job_id} at {minutes_to_hhmm(offer.planned_start_min)} "
                                f"(5-min timeout at {offer.expires_at_utc.isoformat()})."
                            ),
                        )
                        return offer
                    self._remove_job_from_route(job_id)

            return self._attempt_next_eligible_technician(
                job_id=job_id,
                now_utc=ts,
                trigger_label="Manual dispatch request",
            )

    def offer_all_pending(self, now_utc: datetime | None = None) -> list[AssignmentOffer]:
        """Issue 5-minute offers in deterministic priority order for all PLANNED_UNOFFERED jobs."""
        with self._lock:
            ts = _normalize_utc(now_utc)
            self.last_updated_utc = ts
            unoffered_ids = sorted(
                (
                    jid
                    for jid, rec in self._job_records.items()
                    if rec.dispatch_status == JobDispatchStatus.PLANNED_UNOFFERED
                ),
                key=lambda jid: (
                    self._active_jobs_by_id[jid].priority.rank,
                    self._job_records[jid].planned_start_min or 0,
                    jid,
                ),
            )
            issued: list[AssignmentOffer] = []
            for jid in unoffered_ids:
                off = self.offer_job(jid, now_utc=ts)
                if off is not None:
                    issued.append(off)
            return issued

    def _expire_single_offer(
        self,
        offer: AssignmentOffer,
        now_utc: datetime,
        auto_retry: bool,
    ) -> AssignmentOffer | None:
        """Transition a single expired offer to TIMED_OUT and optionally retry next technician."""
        job_id = offer.job_id
        rec = self._job_records[job_id]
        offer.status = OfferStatus.TIMED_OUT
        offer.responded_at_utc = now_utc
        offer.response_reason = (
            f"No response within {self.dispatch_config.response_timeout_seconds}s timeout."
        )
        if offer.technician_id not in rec.excluded_technician_ids:
            rec.excluded_technician_ids.append(offer.technician_id)
        rec.active_offer_id = None
        self._remove_job_from_route(job_id)

        self._record_event(
            timestamp_utc=now_utc,
            job_id=job_id,
            event_type="offer_timed_out",
            offer_id=offer.offer_id,
            technician_id=offer.technician_id,
            attempt_number=offer.attempt_number,
            summary=(
                f"Offer {offer.offer_id} on {offer.technician_id} timed out at "
                f"{now_utc.isoformat()} (deadline {offer.expires_at_utc.isoformat()})."
            ),
        )

        if auto_retry:
            return self._attempt_next_eligible_technician(
                job_id=job_id,
                now_utc=now_utc,
                trigger_label=f"Retry after timeout on {offer.technician_id}",
            )

        rec.dispatch_status = JobDispatchStatus.EXHAUSTED_UNASSIGNED
        rec.assigned_technician_id = None
        rec.planned_start_min = None
        rec.planned_completion_min = None
        return None

    def respond_to_offer(
        self,
        offer_id: str,
        technician_id: str,
        decision: str,
        reason: str | None = None,
        responded_at_utc: datetime | None = None,
    ) -> DispatchActionResponse:
        """Process technician 'accept' or 'reject' with stale-offer and timeout enforcement."""
        with self._lock:
            ts = _normalize_utc(responded_at_utc)
            self.last_updated_utc = ts

            offer = self._offers_by_id.get(offer_id)
            if offer is None:
                raise OfferNotFoundError(f"Assignment offer '{offer_id}' does not exist.")

            job_id = offer.job_id
            rec = self._job_records[job_id]

            if offer.technician_id != technician_id:
                self._record_event(
                    timestamp_utc=ts,
                    job_id=job_id,
                    event_type="stale_or_conflicting_attempt_blocked",
                    offer_id=offer_id,
                    technician_id=technician_id,
                    attempt_number=offer.attempt_number,
                    summary=(
                        f"Blocked response on {offer_id} from '{technician_id}' "
                        f"(expected '{offer.technician_id}')."
                    ),
                )
                raise DispatchConflictError(
                    "TECHNICIAN_MISMATCH",
                    f"Offer '{offer_id}' belongs to technician '{offer.technician_id}', not '{technician_id}'.",
                )

            if offer.status != OfferStatus.PENDING_RESPONSE or rec.active_offer_id != offer_id:
                self._record_event(
                    timestamp_utc=ts,
                    job_id=job_id,
                    event_type="stale_or_conflicting_attempt_blocked",
                    offer_id=offer_id,
                    technician_id=technician_id,
                    attempt_number=offer.attempt_number,
                    summary=(
                        f"Blocked stale/duplicate '{decision}' on {offer_id} from {technician_id} "
                        f"(current offer status='{offer.status.value}', active_offer='{rec.active_offer_id}')."
                    ),
                )
                if offer.status == OfferStatus.ACCEPTED:
                    raise DispatchConflictError(
                        "OFFER_ALREADY_FINALIZED",
                        f"Offer '{offer_id}' was already accepted by '{offer.technician_id}'.",
                    )
                raise StaleOfferError(
                    "STALE_OFFER_SUPERSEDED",
                    f"Offer '{offer_id}' is no longer active (status='{offer.status.value}').",
                )

            # Enforce 5-minute timeout boundary BEFORE accepting or rejecting
            if ts >= offer.expires_at_utc:
                self._expire_single_offer(
                    offer=offer,
                    now_utc=ts,
                    auto_retry=self.dispatch_config.auto_retry_on_timeout,
                )
                self._record_event(
                    timestamp_utc=ts,
                    job_id=job_id,
                    event_type="stale_or_conflicting_attempt_blocked",
                    offer_id=offer_id,
                    technician_id=technician_id,
                    attempt_number=offer.attempt_number,
                    summary=(
                        f"Rejected late '{decision}' from {technician_id} on {offer_id} at "
                        f"{ts.isoformat()} after 5-minute deadline {offer.expires_at_utc.isoformat()}."
                    ),
                )
                raise StaleOfferError(
                    "STALE_OFFER_EXPIRED",
                    f"Offer '{offer_id}' expired at {offer.expires_at_utc.isoformat()} before response at {ts.isoformat()}.",
                )

            norm_decision = decision.strip().lower()
            if norm_decision == "accept":
                located = self._find_stop(job_id)
                if located is None or located[0] != technician_id:
                    raise DispatchConflictError(
                        "ROUTE_STATE_CONFLICT",
                        f"Reserved stop for '{job_id}' is missing on '{technician_id}'.",
                    )
                _, _, stop = located
                stop.is_protected = True
                stop.status = JobStatus.ASSIGNED.value

                val = validate_full_schedule(
                    routes_by_tech=self._routes_by_tech,
                    electricians_by_id=self._elecs_by_id,
                    valid_jobs_by_id=self._active_jobs_by_id,
                    unavailability_by_tech=self._unavail_by_tech,
                    existing_assignments=self._effective_existing_commitments(),
                    travel_matrix=self._travel_matrix,
                    config=self.scheduler_config,
                )
                if not val.is_valid:
                    raise DispatchConflictError(
                        "VALIDATION_FAILED_ON_ACCEPT",
                        f"Schedule validation failed on accepting '{offer_id}': {'; '.join(val.errors)}",
                    )

                offer.status = OfferStatus.ACCEPTED
                offer.responded_at_utc = ts
                offer.response_reason = reason
                rec.dispatch_status = JobDispatchStatus.ACCEPTED
                rec.assigned_technician_id = technician_id
                rec.active_offer_id = None

                self._record_event(
                    timestamp_utc=ts,
                    job_id=job_id,
                    event_type="offer_accepted",
                    offer_id=offer_id,
                    technician_id=technician_id,
                    attempt_number=offer.attempt_number,
                    summary=(
                        f"Technician {technician_id} accepted offer {offer_id} for job {job_id} "
                        f"({minutes_to_hhmm(offer.planned_start_min)}-{minutes_to_hhmm(offer.planned_completion_min)})."
                    ),
                )
                return DispatchActionResponse(
                    run_id=self.run_id,
                    action="offer_accepted",
                    affected_job_ids=[job_id],
                    state=self.snapshot(),
                )

            if norm_decision == "reject":
                offer.status = OfferStatus.REJECTED
                offer.responded_at_utc = ts
                offer.response_reason = reason or "Rejected by technician"
                if technician_id not in rec.excluded_technician_ids:
                    rec.excluded_technician_ids.append(technician_id)
                rec.active_offer_id = None
                self._remove_job_from_route(job_id)

                self._record_event(
                    timestamp_utc=ts,
                    job_id=job_id,
                    event_type="offer_rejected",
                    offer_id=offer_id,
                    technician_id=technician_id,
                    attempt_number=offer.attempt_number,
                    summary=(
                        f"Technician {technician_id} rejected offer {offer_id} for job {job_id}"
                        + (f" ({reason})." if reason else ".")
                    ),
                )

                new_offers: list[AssignmentOffer] = []
                exhausted_ids: list[str] = []
                if self.dispatch_config.auto_retry_on_reject:
                    retry_offer = self._attempt_next_eligible_technician(
                        job_id=job_id,
                        now_utc=ts,
                        trigger_label=f"Retry after rejection by {technician_id}",
                    )
                    if retry_offer is not None:
                        new_offers.append(retry_offer)
                    else:
                        exhausted_ids.append(job_id)
                else:
                    rec.dispatch_status = JobDispatchStatus.EXHAUSTED_UNASSIGNED
                    rec.assigned_technician_id = None
                    rec.planned_start_min = None
                    rec.planned_completion_min = None
                    exhausted_ids.append(job_id)

                return DispatchActionResponse(
                    run_id=self.run_id,
                    action="offer_rejected",
                    affected_job_ids=[job_id],
                    new_offers=new_offers,
                    exhausted_job_ids=exhausted_ids,
                    state=self.snapshot(),
                )

            raise DispatchError("INVALID_DECISION", f"Unsupported decision '{decision}'. Expected 'accept' or 'reject'.")

    def sweep_timeouts(self, now_utc: datetime | None = None) -> DispatchActionResponse:
        """Expire all pending offers whose 5-minute deadline has elapsed (`now_utc >= expires_at_utc`) and retry."""
        with self._lock:
            ts = _normalize_utc(now_utc)
            self.last_updated_utc = ts

            expired_offers = sorted(
                (
                    self._offers_by_id[rec.active_offer_id]
                    for rec in self._job_records.values()
                    if rec.dispatch_status == JobDispatchStatus.PENDING_RESPONSE
                    and rec.active_offer_id is not None
                    and ts >= self._offers_by_id[rec.active_offer_id].expires_at_utc
                ),
                key=lambda o: (
                    self._active_jobs_by_id[o.job_id].priority.rank,
                    o.expires_at_utc,
                    o.job_id,
                ),
            )

            timed_out_ids: list[str] = []
            affected_jobs: list[str] = []
            new_offers: list[AssignmentOffer] = []
            exhausted_ids: list[str] = []

            for exp_off in expired_offers:
                timed_out_ids.append(exp_off.offer_id)
                affected_jobs.append(exp_off.job_id)
                retry_off = self._expire_single_offer(
                    offer=exp_off,
                    now_utc=ts,
                    auto_retry=self.dispatch_config.auto_retry_on_timeout,
                )
                if retry_off is not None:
                    new_offers.append(retry_off)
                else:
                    exhausted_ids.append(exp_off.job_id)

            return DispatchActionResponse(
                run_id=self.run_id,
                action="sweep_timeouts",
                affected_job_ids=affected_jobs,
                timed_out_offer_ids=timed_out_ids,
                new_offers=new_offers,
                exhausted_job_ids=exhausted_ids,
                state=self.snapshot(),
            )

    def _materialize_schedule_snapshot(self) -> ScheduleSnapshot:
        """Build a full-validated, objective-consistent ScheduleSnapshot reflecting live dispatch state."""
        eff_existing = self._effective_existing_commitments()
        validation = validate_full_schedule(
            routes_by_tech=self._routes_by_tech,
            electricians_by_id=self._elecs_by_id,
            valid_jobs_by_id=self._active_jobs_by_id,
            unavailability_by_tech=self._unavail_by_tech,
            existing_assignments=eff_existing,
            travel_matrix=self._travel_matrix,
            config=self.scheduler_config,
        )
        objective = evaluate_schedule_objective(
            routes_by_tech=self._routes_by_tech,
            electricians=self._electricians,
            active_jobs_by_id=self._active_jobs_by_id,
            validation=validation,
            config=self.scheduler_config,
        )
        workloads = compute_technician_workloads(self._electricians, self._routes_by_tech)

        scheduled_assignments: list[ScheduledAssignment] = []
        assigned_ids: list[str] = []
        urgencies: list[float] = []

        for tid in sorted(self._routes_by_tech.keys()):
            route = self._routes_by_tech[tid]
            elec = self._elecs_by_id[tid]
            for pos, stop in enumerate(route):
                skip_travel: int | None = None
                if pos + 1 < len(route):
                    skip_res = self._travel_matrix.lookup(
                        stop.from_location_id, route[pos + 1].job.location_id
                    )
                    skip_travel = skip_res.travel_time_min if skip_res is not None else None
                inc_travel = compute_incremental_travel_for_stop(route, pos, skip_travel)

                rec = self._job_records.get(stop.job.job_id)
                latest_expl = (
                    rec.offers[-1].selection_explanation
                    if rec and rec.offers and rec.offers[-1].technician_id == tid
                    else None
                )
                if latest_expl is None:
                    elig_e, _ = get_static_eligible_electricians(stop.job, self._electricians)
                    ev_ph = CandidateEvaluationResult(
                        job=stop.job,
                        static_eligible_ids=[e.technician_id for e in elig_e],
                    )
                    latest_expl = build_assignment_explanation(
                        stop=stop,
                        route_position=pos,
                        route_length=len(route),
                        incremental_travel_min=inc_travel,
                        electrician=elec,
                        greedy_eval=ev_ph,
                        config=self.scheduler_config,
                    )

                urg = compute_soft_sla_urgency(stop.slack_min, self.scheduler_config.urgency_horizon_min)
                urgencies.append(urg)
                assigned_ids.append(stop.job.job_id)

                scheduled_assignments.append(
                    ScheduledAssignment(
                        job_id=stop.job.job_id,
                        technician_id=tid,
                        priority=stop.job.priority,
                        route_position=pos,
                        from_location_id=stop.from_location_id,
                        departure_min=stop.departure_min,
                        arrival_min=stop.arrival_min,
                        planned_start_min=stop.planned_start_min,
                        completion_min=stop.completion_min,
                        departure_hhmm=minutes_to_hhmm(stop.departure_min),
                        arrival_hhmm=minutes_to_hhmm(stop.arrival_min),
                        planned_start_hhmm=minutes_to_hhmm(stop.planned_start_min),
                        completion_hhmm=minutes_to_hhmm(stop.completion_min),
                        planned_start_utc=minutes_to_utc_datetime(
                            stop.planned_start_min, self.scheduler_config.service_date
                        ),
                        planned_arrival_utc=minutes_to_utc_datetime(
                            stop.arrival_min, self.scheduler_config.service_date
                        ),
                        planned_completion_utc=minutes_to_utc_datetime(
                            stop.completion_min, self.scheduler_config.service_date
                        ),
                        travel_time_min=stop.travel_time_min,
                        incremental_travel_min=inc_travel,
                        service_duration_min=stop.job.duration_min,
                        sla_deadline_min=stop.job.sla_deadline_min,
                        slack_min=stop.slack_min,
                        soft_sla_urgency=urg,
                        is_hard_deadline=stop.job.is_hard_deadline,
                        travel_estimate_source=stop.travel_source,
                        status=stop.status,
                        is_protected=stop.is_protected,
                        changed_by_optimizer=False,
                        explanation=latest_expl,
                    )
                )

        assigned_set = set(assigned_ids)
        unassigned_reports: list[UnassignedJobReport] = []
        for jid in sorted(self._active_jobs_by_id.keys()):
            if jid in assigned_set:
                continue
            rec = self._job_records.get(jid)
            if rec and rec.final_unassigned_reason is not None:
                unassigned_reports.append(rec.final_unassigned_reason)
            else:
                rjob = self._active_jobs_by_id[jid]
                final_ev = generate_candidates_for_job(
                    job=rjob,
                    electricians=self._electricians,
                    routes_by_tech=self._routes_by_tech,
                    unavailability_by_tech=self._unavail_by_tech,
                    travel_matrix=self._travel_matrix,
                    config=self.scheduler_config,
                )
                unassigned_reports.append(
                    build_unassigned_job_report(
                        job=rjob,
                        final_eval=final_ev,
                        isolated_eval=self._isolated_evals[jid],
                        all_electricians=self._electricians,
                    )
                )

        for jid in sorted(self._invalid_job_reports.keys()):
            unassigned_reports.append(self._invalid_job_reports[jid])
        unassigned_reports.sort(key=lambda r: r.job_id)

        if self._invalid_job_reports:
            objective.unassigned_count += len(self._invalid_job_reports)

        high_prio_unassigned = sum(
            1
            for r in unassigned_reports
            if r.priority.strip().lower() in ("critical", "p1", "high", "p2")
        )
        mean_urg = round(sum(urgencies) / float(len(urgencies)), 4) if urgencies else 0.0
        max_urg = round(max(urgencies), 4) if urgencies else 0.0

        return ScheduleSnapshot(
            stage="final_optimized",
            assignments=scheduled_assignments,
            assigned_job_ids=sorted(assigned_ids),
            unassigned_job_ids=[r.job_id for r in unassigned_reports],
            unassigned_reports=unassigned_reports,
            technician_workloads=workloads,
            total_travel_min=objective.raw_total_travel_min,
            total_service_min=objective.raw_total_service_min,
            hard_constraint_violation_count=validation.hard_violation_count,
            hard_sla_violation_count=validation.hard_sla_violation_count,
            predicted_soft_sla_breach_count=objective.predicted_soft_sla_breach_count,
            mean_soft_sla_urgency=mean_urg,
            max_soft_sla_urgency=max_urg,
            high_priority_unassigned_count=high_prio_unassigned,
            objective=objective,
            is_valid_for_commitment=validation.is_valid,
            validation_errors=validation.errors,
        )

    def snapshot(self) -> DispatchStateSnapshot:
        """Return an immutable Pydantic snapshot of current dispatch state and live schedule."""
        with self._lock:
            sched_snap = self._materialize_schedule_snapshot()
            counts = Counter(rec.dispatch_status for rec in self._job_records.values())
            cloned_states = {
                jid: rec.model_copy(deep=True)
                for jid, rec in sorted(self._job_records.items())
            }
            return DispatchStateSnapshot(
                run_id=self.run_id,
                dispatch_config=self.dispatch_config.model_copy(deep=True),
                created_at_utc=self.created_at_utc,
                last_updated_utc=self.last_updated_utc,
                is_valid_for_commitment=sched_snap.is_valid_for_commitment,
                pending_offer_count=counts[JobDispatchStatus.PENDING_RESPONSE],
                accepted_count=counts[JobDispatchStatus.ACCEPTED],
                locked_committed_count=counts[JobDispatchStatus.LOCKED_COMMITTED],
                exhausted_unassigned_count=counts[JobDispatchStatus.EXHAUSTED_UNASSIGNED],
                job_states=cloned_states,
                events=[e.model_copy(deep=True) for e in self._events],
                current_schedule=sched_snap,
            )


class DispatchSessionStore:
    """Thread-safe in-memory repository of active DispatchSession coordinators."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, DispatchSession] = {}

    def put(self, session: DispatchSession) -> None:
        with self._lock:
            self._sessions[session.run_id] = session

    def get(self, run_id: str) -> DispatchSession | None:
        with self._lock:
            return self._sessions.get(run_id)
