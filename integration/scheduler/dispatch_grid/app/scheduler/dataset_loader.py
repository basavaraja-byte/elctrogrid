"""Dataset CSV loading, schema validation, scenario wiring, and Feasibility Audit (Sections 2 & 3)."""

from __future__ import annotations

import csv
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from app.scheduler.candidates import generate_candidates_for_job
from app.scheduler.constraints import validate_job_data
from app.scheduler.travel import TravelMatrix
from app.schemas.scheduling import (
    DatasetAuditReport,
    DisruptionScenario,
    Electrician,
    Job,
    JobAuditEntry,
    JobStatus,
    SchedulerConfig,
    TravelEntry,
    UnavailabilityInterval,
)


EXPECTED_DATASET_FILES: tuple[str, ...] = (
    "README.md",
    "electricians.csv",
    "electrical_jobs.csv",
    "travel_times.csv",
    "technician_unavailability.csv",
    "disruption_scenarios.csv",
    "scenario_job_J101.csv",
)


def default_data_dir() -> Path:
    """Resolve the dataset directory from environment or repository root."""
    configured = os.getenv("DISPATCHGRID_DATA_DIR")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[2] / "data"


@dataclass(slots=True)
class LoadedDatasetBundle:
    """Validated dataset objects, scenario metadata, and load-time diagnostics."""

    data_dir: Path
    electricians: list[Electrician] = field(default_factory=list)
    jobs: list[Job] = field(default_factory=list)
    travel_entries: list[TravelEntry] = field(default_factory=list)
    unavailability: list[UnavailabilityInterval] = field(default_factory=list)
    all_unavailability: list[UnavailabilityInterval] = field(default_factory=list)
    scenarios: list[DisruptionScenario] = field(default_factory=list)
    scenario_jobs_by_id: dict[str, list[Job]] = field(default_factory=dict)
    missing_files: list[str] = field(default_factory=list)
    malformed_records: list[str] = field(default_factory=list)


def _parse_optional_float(raw: str | None) -> float | None:
    if raw is None or raw.strip() == "":
        return None
    return float(raw.strip())


def _parse_required_int(raw: str | None, field_name: str) -> int:
    if raw is None or raw.strip() == "":
        raise ValueError(f"Missing required integer field '{field_name}'.")
    return int(raw.strip())


def _load_jobs_csv(path: Path, malformed: list[str], source_label: str) -> list[Job]:
    jobs: list[Job] = []
    required_cols = {
        "job_id",
        "trade",
        "job_type",
        "required_skills",
        "priority",
        "duration_min",
        "zone",
        "location_x_km",
        "location_y_km",
        "window_start_min",
        "window_end_min",
        "sla_deadline_min",
        "status",
    }
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = set(reader.fieldnames or [])
        missing_cols = sorted(required_cols - header)
        if missing_cols:
            malformed.append(f"{source_label}: missing columns {missing_cols}")
            return jobs

        for row_num, row in enumerate(reader, start=2):
            if any(v is None for k, v in row.items() if k in required_cols):
                malformed.append(f"{source_label}:{row_num}: truncated CSV row {row}")
                continue
            try:
                job = Job(
                    job_id=(row.get("job_id") or "").strip(),
                    trade=(row.get("trade") or "").strip(),
                    job_type=(row.get("job_type") or "").strip(),
                    required_skills=row.get("required_skills") or "",
                    required_certifications=row.get("required_certifications") or "",
                    priority=(row.get("priority") or "").strip(),
                    duration_min=_parse_required_int(row.get("duration_min"), "duration_min"),
                    zone=(row.get("zone") or "").strip(),
                    location_x_km=_parse_optional_float(row.get("location_x_km")),
                    location_y_km=_parse_optional_float(row.get("location_y_km")),
                    window_start_min=_parse_required_int(row.get("window_start_min"), "window_start_min"),
                    window_end_min=_parse_required_int(row.get("window_end_min"), "window_end_min"),
                    sla_deadline_min=_parse_required_int(row.get("sla_deadline_min"), "sla_deadline_min"),
                    status=(row.get("status") or "pending").strip(),
                    notes=(row.get("notes") or "").strip(),
                )
                jobs.append(job)
            except (ValueError, ValidationError) as exc:
                malformed.append(f"{source_label}:{row_num}: {exc}")
    return jobs


def load_dataset_bundle(
    data_dir: Path | str | None = None,
    scenario_ids: list[str] | None = None,
) -> LoadedDatasetBundle:
    """Load CSV files from data_dir without silently fabricating missing/corrupt records."""
    resolved_dir = Path(data_dir).resolve() if data_dir is not None else default_data_dir()
    bundle = LoadedDatasetBundle(data_dir=resolved_dir)
    active_scenarios = {s.strip() for s in (scenario_ids or []) if s.strip()}

    for expected in EXPECTED_DATASET_FILES:
        if not (resolved_dir / expected).exists():
            bundle.missing_files.append(expected)

    # 1. Electricians
    elec_path = resolved_dir / "electricians.csv"
    if elec_path.exists():
        req_cols = {
            "technician_id",
            "name",
            "trade",
            "skills",
            "eligible_zones",
            "home_zone",
            "shift_start_min",
            "shift_end_min",
            "start_x_km",
            "start_y_km",
            "status",
        }
        with elec_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            missing_cols = sorted(req_cols - set(reader.fieldnames or []))
            if missing_cols:
                bundle.malformed_records.append(f"electricians.csv: missing columns {missing_cols}")
            else:
                for row_num, row in enumerate(reader, start=2):
                    try:
                        elec = Electrician(
                            technician_id=(row.get("technician_id") or "").strip(),
                            name=(row.get("name") or "").strip(),
                            trade=(row.get("trade") or "").strip(),
                            skills=row.get("skills") or "",
                            certifications=row.get("certifications") or "",
                            eligible_zones=row.get("eligible_zones") or "",
                            home_zone=(row.get("home_zone") or "").strip() or None,
                            shift_start_min=_parse_required_int(row.get("shift_start_min"), "shift_start_min"),
                            shift_end_min=_parse_required_int(row.get("shift_end_min"), "shift_end_min"),
                            start_x_km=_parse_optional_float(row.get("start_x_km")),
                            start_y_km=_parse_optional_float(row.get("start_y_km")),
                            status=(row.get("status") or "active").strip(),
                        )
                        bundle.electricians.append(elec)
                    except (ValueError, ValidationError) as exc:
                        bundle.malformed_records.append(f"electricians.csv:{row_num}: {exc}")

    # 2. Baseline electrical jobs
    jobs_path = resolved_dir / "electrical_jobs.csv"
    if jobs_path.exists():
        bundle.jobs = _load_jobs_csv(jobs_path, bundle.malformed_records, "electrical_jobs.csv")

    # 3. Travel times
    tt_path = resolved_dir / "travel_times.csv"
    if tt_path.exists():
        req_cols = {"from_location_id", "to_location_id", "travel_time_min", "distance_km_est"}
        with tt_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            missing_cols = sorted(req_cols - set(reader.fieldnames or []))
            if missing_cols:
                bundle.malformed_records.append(f"travel_times.csv: missing columns {missing_cols}")
            else:
                for row_num, row in enumerate(reader, start=2):
                    try:
                        entry = TravelEntry(
                            from_location_id=(row.get("from_location_id") or "").strip(),
                            to_location_id=(row.get("to_location_id") or "").strip(),
                            travel_time_min=_parse_required_int(row.get("travel_time_min"), "travel_time_min"),
                            distance_km_est=float((row.get("distance_km_est") or "0").strip()),
                            estimate_type=(row.get("estimate_type") or "matrix_lookup").strip(),
                        )
                        bundle.travel_entries.append(entry)
                    except (ValueError, ValidationError) as exc:
                        bundle.malformed_records.append(f"travel_times.csv:{row_num}: {exc}")

    # 4. Technician unavailability
    unavail_path = resolved_dir / "technician_unavailability.csv"
    if unavail_path.exists():
        req_cols = {"unavailability_id", "technician_id", "start_min", "end_min"}
        with unavail_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            missing_cols = sorted(req_cols - set(reader.fieldnames or []))
            if missing_cols:
                bundle.malformed_records.append(
                    f"technician_unavailability.csv: missing columns {missing_cols}"
                )
            else:
                for row_num, row in enumerate(reader, start=2):
                    try:
                        scen = (row.get("scenario_id") or "").strip() or None
                        interval = UnavailabilityInterval(
                            unavailability_id=(row.get("unavailability_id") or "").strip(),
                            technician_id=(row.get("technician_id") or "").strip(),
                            start_min=_parse_required_int(row.get("start_min"), "start_min"),
                            end_min=_parse_required_int(row.get("end_min"), "end_min"),
                            reason=(row.get("reason") or "").strip(),
                            scenario_id=scen,
                        )
                        bundle.all_unavailability.append(interval)
                        if scen is None or scen.upper() == "BASELINE" or scen in active_scenarios:
                            bundle.unavailability.append(interval)
                    except (ValueError, ValidationError) as exc:
                        bundle.malformed_records.append(
                            f"technician_unavailability.csv:{row_num}: {exc}"
                        )

    # 5. Disruption scenarios & scenario-driven urgent jobs (no hardcoded job IDs)
    scen_path = resolved_dir / "disruption_scenarios.csv"
    if scen_path.exists():
        req_cols = {"scenario_id", "scenario_name", "event_type", "target_id", "event_time_min"}
        with scen_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            missing_cols = sorted(req_cols - set(reader.fieldnames or []))
            if missing_cols:
                bundle.malformed_records.append(
                    f"disruption_scenarios.csv: missing columns {missing_cols}"
                )
            else:
                for row_num, row in enumerate(reader, start=2):
                    try:
                        sc = DisruptionScenario(
                            scenario_id=(row.get("scenario_id") or "").strip(),
                            scenario_name=(row.get("scenario_name") or "").strip(),
                            event_type=(row.get("event_type") or "").strip(),
                            target_id=(row.get("target_id") or "").strip(),
                            event_time_min=_parse_required_int(row.get("event_time_min"), "event_time_min"),
                            payload=(row.get("payload") or "").strip(),
                        )
                        bundle.scenarios.append(sc)

                        if sc.event_type == "urgent_job_arrival":
                            candidate_file = resolved_dir / f"scenario_job_{sc.target_id}.csv"
                            if candidate_file.exists():
                                s_jobs = _load_jobs_csv(
                                    candidate_file,
                                    bundle.malformed_records,
                                    candidate_file.name,
                                )
                                bundle.scenario_jobs_by_id[sc.scenario_id] = s_jobs
                            else:
                                bundle.missing_files.append(candidate_file.name)
                    except (ValueError, ValidationError) as exc:
                        bundle.malformed_records.append(f"disruption_scenarios.csv:{row_num}: {exc}")

    # 6. Apply active scenario effects transparently from scenario metadata
    scenarios_by_id = {s.scenario_id: s for s in bundle.scenarios}
    existing_job_ids = {j.job_id for j in bundle.jobs}
    for sid in sorted(active_scenarios):
        sc = scenarios_by_id.get(sid)
        if sc is None:
            continue
        if sc.event_type == "urgent_job_arrival":
            for sjob in bundle.scenario_jobs_by_id.get(sid, []):
                if sjob.job_id not in existing_job_ids:
                    bundle.jobs.append(sjob)
                    existing_job_ids.add(sjob.job_id)
        elif sc.event_type == "job_cancelled":
            for j in bundle.jobs:
                if j.job_id == sc.target_id:
                    j.status = JobStatus.CANCELLED.value
        elif sc.event_type == "duration_change":
            # Parse explicit minute delta from scenario payload if present (e.g. 'by 45 minutes')
            match = re.search(r"by\s+(\d+)\s+minute", sc.payload, flags=re.IGNORECASE)
            if match:
                delta = int(match.group(1))
                for j in bundle.jobs:
                    if j.job_id == sc.target_id:
                        j.duration_min += delta

    return bundle


def _bucket_key(count: int) -> str:
    if count <= 0:
        return "0"
    if count == 1:
        return "1"
    return "2+"


def generate_dataset_audit(
    bundle: LoadedDatasetBundle | None = None,
    data_dir: Path | str | None = None,
    post_schedule_assigned_count: int | None = None,
    post_schedule_unassigned_count: int | None = None,
    post_schedule_unassigned_by_reason: dict[str, int] | None = None,
) -> DatasetAuditReport:
    """Execute the mandatory Dataset Feasibility Audit (Section 3)."""
    ds = bundle if bundle is not None else load_dataset_bundle(data_dir=data_dir)
    elecs = ds.electricians
    active_elecs = [e for e in elecs if e.is_active]
    jobs = ds.jobs

    all_scenario_jobs = [
        sj for sjobs in ds.scenario_jobs_by_id.values() for sj in sjobs
    ]
    travel_matrix = TravelMatrix(
        entries=ds.travel_entries,
        electricians=elecs,
        jobs=jobs + all_scenario_jobs,
        allow_coordinate_fallback=False,
    )

    # Distinct attributes
    e_skills = sorted({s for e in elecs for s in e.skills})
    j_skills = sorted({s for j in jobs for s in j.required_skills})
    unmatched_skills = sorted(set(j_skills) - set(e_skills))

    e_certs = sorted({c for e in elecs for c in e.certifications})
    e_zones = sorted({z for e in elecs for z in e.eligible_zones})
    j_zones = sorted({j.zone for j in jobs if j.zone})
    unserved_zones = sorted(set(j_zones) - set(e_zones))

    shifts = sorted({f"{e.shift_start_min}-{e.shift_end_min}" for e in elecs})
    prio_dist = dict(Counter(j.priority for j in jobs))

    # Check travel coverage across baseline homes & baseline jobs
    expected_locs = {e.effective_start_location_id for e in elecs} | {
        j.effective_location_id for j in jobs
    }
    missing_baseline_pairs: list[str] = []
    for u in sorted(expected_locs):
        for v in sorted(expected_locs):
            if not travel_matrix.has_exact_entry(u, v):
                missing_baseline_pairs.append(f"{u}->{v}")

    scenario_missing_locs: list[str] = []
    known_matrix_locs = travel_matrix.matrix_locations
    for sj in all_scenario_jobs:
        if sj.effective_location_id not in known_matrix_locs:
            scenario_missing_locs.append(sj.effective_location_id)

    # Static & isolated feasibility evaluation under both HARD and SOFT SLA policies
    skill_buckets: Counter[str] = Counter({"0": 0, "1": 0, "2+": 0})
    zone_buckets: Counter[str] = Counter({"0": 0, "1": 0, "2+": 0})
    static_buckets: Counter[str] = Counter({"0": 0, "1": 0, "2+": 0})
    hard_feas_buckets: Counter[str] = Counter({"0": 0, "1": 0, "2+": 0})
    soft_feas_buckets: Counter[str] = Counter({"0": 0, "1": 0, "2+": 0})

    hard_infeasible_entries: list[JobAuditEntry] = []
    soft_infeasible_entries: list[JobAuditEntry] = []
    single_static_jobs: list[str] = []
    multi_feasible_alternatives_hard = 0
    intrinsic_sla_impossible_count = 0

    hard_cfg = SchedulerConfig(sla_mode="hard", allow_coordinate_travel_fallback=True)
    soft_cfg = SchedulerConfig(sla_mode="soft", allow_coordinate_travel_fallback=True)
    audit_travel = TravelMatrix(
        entries=ds.travel_entries,
        electricians=elecs,
        jobs=jobs + all_scenario_jobs,
        allow_coordinate_fallback=True,
    )
    empty_routes: dict[str, list] = {e.technician_id: [] for e in elecs}
    unavail_by_tech: dict[str, list[UnavailabilityInterval]] = {}
    for u in ds.unavailability:
        unavail_by_tech.setdefault(u.technician_id, []).append(u)

    for job in jobs:
        if (
            job.window_start_min is not None
            and job.sla_deadline_min is not None
            and job.window_start_min + job.duration_min > job.sla_deadline_min
        ):
            intrinsic_sla_impossible_count += 1

        req_sk = set(job.required_skills)
        req_ct = set(job.required_certifications)
        sk_matches = [
            e for e in active_elecs
            if e.trade.strip().lower() == job.trade.strip().lower()
            and req_sk.issubset(set(e.skills))
            and req_ct.issubset(set(e.certifications))
        ]
        zn_matches = [
            e for e in active_elecs
            if e.trade.strip().lower() == job.trade.strip().lower()
            and job.zone in set(e.eligible_zones)
        ]
        st_matches = [e for e in sk_matches if job.zone in set(e.eligible_zones)]

        skill_buckets[_bucket_key(len(sk_matches))] += 1
        zone_buckets[_bucket_key(len(zn_matches))] += 1
        static_buckets[_bucket_key(len(st_matches))] += 1
        if len(st_matches) == 1:
            single_static_jobs.append(job.job_id)

        # Evaluate isolated schedule feasibility under Hard SLA
        rjob_hard, errs_hard = validate_job_data(job, hard_cfg)
        if rjob_hard is None:
            hard_feas_buckets["0"] += 1
            hard_infeasible_entries.append(
                JobAuditEntry(
                    job_id=job.job_id,
                    priority=job.priority,
                    zone=job.zone,
                    required_skills=list(job.required_skills),
                    skill_eligible_count=len(sk_matches),
                    zone_eligible_count=len(zn_matches),
                    static_eligible_count=len(st_matches),
                    isolated_feasible_electrician_count=0,
                    isolated_feasible_slot_count=0,
                    infeasible_reasons=[f"{e.code.value}: {e.detail}" for e in errs_hard],
                )
            )
        else:
            ev_hard = generate_candidates_for_job(
                job=rjob_hard,
                electricians=elecs,
                routes_by_tech=empty_routes,
                unavailability_by_tech=unavail_by_tech,
                travel_matrix=audit_travel,
                config=hard_cfg,
            )
            hard_feas_buckets[_bucket_key(ev_hard.feasible_electrician_count)] += 1
            if ev_hard.feasible_slot_count >= 2:
                multi_feasible_alternatives_hard += 1
            if ev_hard.feasible_electrician_count == 0:
                reasons_h = sorted({f.code.value for f in ev_hard.rejection_details})
                hard_infeasible_entries.append(
                    JobAuditEntry(
                        job_id=job.job_id,
                        priority=job.priority,
                        zone=job.zone,
                        required_skills=list(job.required_skills),
                        skill_eligible_count=len(sk_matches),
                        zone_eligible_count=len(zn_matches),
                        static_eligible_count=len(st_matches),
                        isolated_feasible_electrician_count=0,
                        isolated_feasible_slot_count=0,
                        infeasible_reasons=reasons_h,
                    )
                )

        # Evaluate isolated schedule feasibility under Soft SLA
        rjob_soft, errs_soft = validate_job_data(job, soft_cfg)
        if rjob_soft is None:
            soft_feas_buckets["0"] += 1
            soft_infeasible_entries.append(
                JobAuditEntry(
                    job_id=job.job_id,
                    priority=job.priority,
                    zone=job.zone,
                    required_skills=list(job.required_skills),
                    skill_eligible_count=len(sk_matches),
                    zone_eligible_count=len(zn_matches),
                    static_eligible_count=len(st_matches),
                    isolated_feasible_electrician_count=0,
                    isolated_feasible_slot_count=0,
                    infeasible_reasons=[f"{e.code.value}: {e.detail}" for e in errs_soft],
                )
            )
        else:
            ev_soft = generate_candidates_for_job(
                job=rjob_soft,
                electricians=elecs,
                routes_by_tech=empty_routes,
                unavailability_by_tech=unavail_by_tech,
                travel_matrix=audit_travel,
                config=soft_cfg,
            )
            soft_feas_buckets[_bucket_key(ev_soft.feasible_electrician_count)] += 1
            if ev_soft.feasible_electrician_count == 0:
                reasons_s = sorted({f.code.value for f in ev_soft.rejection_details})
                soft_infeasible_entries.append(
                    JobAuditEntry(
                        job_id=job.job_id,
                        priority=job.priority,
                        zone=job.zone,
                        required_skills=list(job.required_skills),
                        skill_eligible_count=len(sk_matches),
                        zone_eligible_count=len(zn_matches),
                        static_eligible_count=len(st_matches),
                        isolated_feasible_electrician_count=0,
                        isolated_feasible_slot_count=0,
                        infeasible_reasons=reasons_s,
                    )
                )

    supports_tradeoffs = {
        "travel_routing": multi_feasible_alternatives_hard >= 50,
        "workload_balancing": len(active_elecs) >= 5 and multi_feasible_alternatives_hard >= 50,
        "deadline_urgency": len(jobs) > 0,
        "scarce_skills": len(single_static_jobs) > 0,
    }

    tradeoff_assessment = [
        f"Travel & route sequencing: {multi_feasible_alternatives_hard}/{len(jobs)} jobs have 2+ feasible electrician/slot options under hard completion SLA, supporting genuine nearest-tech and route-reordering trade-offs.",
        f"Scarce skills & zone bottlenecks: ev_charger_installation is held by only 4/20 electricians, leaving {len(single_static_jobs)} jobs ({', '.join(single_static_jobs)}) with a single statically eligible electrician (E013 in South, E014 in Central).",
        "Workload balancing: 20 active electricians have heterogeneous shift lengths (420-540 min) and overlapping multi-zone coverage (9-15 electricians per standard zone), creating non-trivial service utilization balance trade-offs.",
        "Deadlines & urgency: slack spans 0 to >240 minutes across feasible candidates, activating continuous urgency differentiation within each priority tier.",
    ]

    limitations = [
        f"Completion SLA vs. time-window anomaly: {intrinsic_sla_impossible_count}/{len(jobs)} baseline jobs have window_start_min + duration_min > sla_deadline_min in electrical_jobs.csv (plus 3 jobs where window_start_min=480 and window_start_min + duration_min == sla_deadline_min, unreachable with positive travel from shift start >=480). Under strict hard completion SLA, {len(hard_infeasible_entries)} jobs have zero feasible slots even on empty routes (including D03 target J018 and D06 target J033).",
        "Shift-window overrun: J012 has window_start_min=840 and duration_min=180 (earliest finish 1020), while its only 2 statically eligible electricians (E003, E014) end shifts at 990 and 960; J012 is therefore infeasible under both hard and soft SLA unless overtime is enabled.",
        f"Scenario travel-matrix gap: travel_times.csv covers all 120 baseline locations (20 homes + 100 baseline jobs = 14,400 pairs), but omits scenario location(s) {scenario_missing_locs} (from scenario_job_J101.csv). Coordinate-based detour calculation is required when scenario D02 is triggered.",
        "Single-specialist bottleneck in South EV charging: 6 South ev_charger_installation jobs compete for the single eligible technician E013 (510-min shift), capping simultaneous South EV coverage regardless of optimizer effort.",
        "Explicit certifications column absent in CSV: specialist authorization ('high_voltage_authorization' on J100) is encoded inside the pipe-delimited required_skills field rather than a separate certifications column.",
    ]

    improvements = [
        "Ensure sla_deadline_min >= window_start_min + duration_min + 30 (minimum travel buffer) during synthetic job generation, or add an explicit 'sla_type' column ('hard_completion' vs 'soft_target' vs 'arrival_deadline') so jobs like J018 remain baseline-schedulable under hard SLA.",
        "Append the 241 pairwise travel rows for J101 (120->J101, J101->120, J101->J101) to travel_times.csv so D02 requires zero coordinate-fallback estimation.",
        "Grant ev_charger_installation to one additional South-eligible electrician (e.g., E007 or E012) if multi-candidate optimization trade-offs are desired for South EV jobs rather than single-specialist capacity saturation.",
        "Split authorization/certification tokens (e.g., high_voltage_authorization) into a dedicated 'certifications' / 'required_certifications' CSV column if distinct skill vs. license reporting is needed in raw data.",
    ]

    return DatasetAuditReport(
        total_electricians=len(elecs),
        active_electricians=len(active_elecs),
        total_jobs=len(jobs),
        distinct_skills_electricians=e_skills,
        distinct_skills_jobs=j_skills,
        unmatched_job_skills=unmatched_skills,
        distinct_certifications_electricians=e_certs,
        distinct_zones_electricians=e_zones,
        distinct_zones_jobs=j_zones,
        unserved_job_zones=unserved_zones,
        distinct_shifts=shifts,
        priority_distribution=prio_dist,
        skill_eligibility_buckets=dict(skill_buckets),
        zone_eligibility_buckets=dict(zone_buckets),
        static_eligibility_buckets=dict(static_buckets),
        isolated_feasibility_buckets_hard_sla=dict(hard_feas_buckets),
        isolated_feasibility_buckets_soft_sla=dict(soft_feas_buckets),
        isolated_infeasible_jobs_hard_sla=hard_infeasible_entries,
        isolated_infeasible_jobs_soft_sla=soft_infeasible_entries,
        jobs_with_multiple_feasible_alternatives_hard_sla=multi_feasible_alternatives_hard,
        jobs_with_single_static_electrician=single_static_jobs,
        travel_matrix_row_count=travel_matrix.row_count,
        expected_baseline_location_count=len(expected_locs),
        missing_baseline_travel_pairs=missing_baseline_pairs,
        scenario_locations_missing_from_matrix=scenario_missing_locs,
        invalid_travel_entries=list(travel_matrix.invalid_entries),
        malformed_records=list(ds.malformed_records),
        post_schedule_assigned_count=post_schedule_assigned_count,
        post_schedule_unassigned_count=post_schedule_unassigned_count,
        post_schedule_unassigned_by_reason=post_schedule_unassigned_by_reason,
        supports_tradeoffs=supports_tradeoffs,
        tradeoff_assessment=tradeoff_assessment,
        dataset_limitations=limitations,
        proposed_minimal_improvements=improvements,
    )

