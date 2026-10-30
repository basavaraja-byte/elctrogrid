# DispatchGrid — Scheduler & Assignment Optimization Engine (Modules B + C)

Intelligent workforce scheduling, hard-constraint validation, and bounded local-search assignment optimization for electrical field-service operations.

---

## Architecture Overview

| Module | File | Responsibility |
|---|---|---|
| **Module B — Hard Constraints** | `app/scheduler/constraints.py` | Intrinsic job validation, static skill/certification/zone checks, shift/unavailability/overlap/SLA rules, and full-schedule commitment validator |
| **Module B — Travel Lookup** | `app/scheduler/travel.py` | Pairwise matrix lookup with explicit missing-data handling (`MISSING_TRAVEL_DATA`) and documented coordinate-detour fallback |
| **Module B — Candidate Engine** | `app/scheduler/candidates.py` | Route-insertion candidate generation across availability gaps, propagating predecessor and successor legs |
| **Module B — Priority & Scarcity** | `app/scheduler/prioritization.py` | Strict business-priority tiers, soft-deadline urgency heuristic ($H=240\text{ min}$), and specialist scarcity protection |
| **Module B — Greedy Scheduler** | `app/scheduler/engine.py` | Deterministic initial schedule construction, commitment preservation, safety gate, and structured run telemetry |
| **Module C — Objective** | `app/scheduler/objective.py` | Normalized weighted cost ($C = w_T C_T + w_S C_S + w_W C_W + w_R C_R$) inside a 7-level lexicographic hierarchy |
| **Module C — Local Search** | `app/scheduler/optimizer.py` | Deterministic bounded local search (unassigned reinsertion + 1-step ejection, intra-route reorder, inter-route relocate, inter-route swap) with cycle prevention |
| **Explainability** | `app/scheduler/explanations.py` | Grounded explanations for assigned routes and evidence-based reason codes for unassigned jobs |
| **Dispatch Timeout & Retry** | `app/scheduler/dispatch.py` | 5-minute (`300`s) technician response timeout, acceptance/rejection, automatic next-eligible technician retry, stale/concurrent attempt guards, and `EXHAUSTED_UNASSIGNED` handling |
| **Disruption Recovery (`D01`–`D07`)** | `app/scheduler/recovery.py` | Reproducible `D01`–`D07` disruption simulator, commitment progression, `IdempotentRequestRegistry` (`D06`), post-recovery validation/objective verification, and per-job recovery explanations |
| **Dataset & Audit** | `app/scheduler/dataset_loader.py` | CSV schema loader, scenario wiring (`D01`–`D07`), and mandatory Dataset Feasibility Audit |
| **FastAPI Routes** | `app/api/routes/scheduling.py`, `dispatch.py`, `recovery.py` | REST endpoints for scheduling, technician offer/timeout/retry, and `D01`–`D07` disruption recovery |

---

## Quick Start (Local, Zero External APIs)

### 1. Create Virtual Environment & Install Dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Start the FastAPI Server

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Interactive OpenAPI docs are served at `http://127.0.0.1:8000/docs`.

### 3. Run the Automated Test Suite

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

### 4. Invoke the Engine Directly from Python

```python
from app.scheduler import generate_dataset_audit, generate_schedule, load_dataset_bundle

bundle = load_dataset_bundle()  # Reads data/*.csv
audit = generate_dataset_audit(bundle)
result = generate_schedule(
    jobs=bundle.jobs,
    electricians=bundle.electricians,
    travel_times=bundle.travel_entries,
    unavailability=bundle.unavailability,
    include_dataset_audit=True,
    dataset_bundle=bundle,
)

print("Valid for commitment:", result.is_valid_for_commitment)
print("Initial greedy assigned:", len(result.initial_greedy_schedule.assigned_job_ids))
print("Final optimized assigned:", len(result.final_schedule.assigned_job_ids))
print("Total travel (min):", result.final_schedule.total_travel_min)
```

---

## REST API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service health check |
| `GET` | `/api/v1/scheduling/audit` | Run mandatory dataset feasibility audit (`?scenario_ids=D02` optional) |
| `POST` | `/api/v1/scheduling/generate` | Generate initial greedy schedule and optionally run Module C optimization |
| `POST` | `/api/v1/scheduling/optimize` | Run/re-run bounded local search on a stored `run_id` or new payload |
| `GET` | `/api/v1/scheduling/current` | Retrieve most recent `ScheduleRunResult` |
| `GET` | `/api/v1/scheduling/current/metrics` | Retrieve objective comparison, workloads, and optimization summary |
| `GET` | `/api/v1/scheduling/current/explanations` | Retrieve per-job assignment explanations and unassigned reason reports |
| `GET` | `/api/v1/scheduling/runs/{run_id}` | Retrieve specific run by `run_id` |
| `GET` | `/api/v1/scheduling/runs/{run_id}/metrics` | Retrieve metrics for `run_id` |
| `GET` | `/api/v1/scheduling/runs/{run_id}/explanations` | Retrieve explanations for `run_id` |
| `POST` | `/api/v1/scheduling/dispatch/runs/{run_id}/init` | Initialize 5-minute technician offer/timeout/retry tracking for `run_id` |
| `GET` | `/api/v1/scheduling/dispatch/runs/{run_id}` | Retrieve live dispatch offer statuses, audit events, and re-validated schedule |
| `POST` | `/api/v1/scheduling/dispatch/runs/{run_id}/offer/{job_id}` | Issue a 5-minute offer for `job_id` (409 on duplicate/concurrent conflict) |
| `POST` | `/api/v1/scheduling/dispatch/runs/{run_id}/respond` | Record technician `"accept"` or `"reject"` with 5-minute timeout & stale-offer guards |
| `POST` | `/api/v1/scheduling/dispatch/runs/{run_id}/sweep-timeouts` | Expire offers past `300`s and automatically attempt next eligible technicians |
| `GET` | `/api/v1/scheduling/recovery/scenarios` | List formal specifications for all 7 disruption scenarios (`D01`–`D07`) |
| `POST` | `/api/v1/scheduling/recovery/simulate` | Simulate a single disruption scenario (`D01`–`D07`) with optional `idempotency_key` |
| `POST` | `/api/v1/scheduling/recovery/simulate-all` | Execute the reproducible `D01`–`D07` recovery simulation suite |
| `POST` | `/api/v1/scheduling/recovery/jobs/idempotent` | Submit a job with idempotency-key deduplication (`D06` protection) |

---

## Priority Policy & Objective Configuration

### Ordering Policy (Section 7)
1. **Hard constraints & protected commitments** enforced prior to candidate scoring.
2. **Business priority** strictly partitions jobs:
   - `Critical` / `P1` (rank 1) > `High` / `P2` (rank 2) > `Normal` / `Medium` / `P3` (rank 3) > `Low` / `P4` (rank 4).
3. **Soft-deadline urgency** within each priority tier:
   $$\text{urgency} = 100 \times \left(1 - \text{clamp}\left(\frac{\text{slack\_minutes}}{H}, 0, 1\right)\right), \quad H = 240\text{ min}$$
4. **Resource scarcity** (fewer feasible electricians, fewer feasible slots, fewer static electricians) plus specialist scarcity-pressure protection during candidate selection.
5. **Deterministic tie-breakers** (`job_id`, `technician_id`, `route_position`).

### Lexicographic Schedule Objective (Section 9)
1. Zero hard-constraint violations (`hard_violation_count == 0`).
2. Zero protected-commitment violations (`protected_violation_count == 0`).
3. Zero hard-SLA deadline violations (`hard_sla_violation_count == 0`; hard-deadline-infeasible candidates rejected before scoring).
4. Maximal feasible job coverage ordered deterministically by business priority (`Critical`, `High`, `Normal`, `Low`) — assigning a feasible job with a predicted soft-SLA breach (`slack_min < 0` when soft deadlines are active) is preferred over leaving it unassigned.
5. Minimal predicted soft-SLA breach count (planning-time risk indicator among equal-coverage schedules, never counted as an actual SLA violation), followed by minimal normalized weighted cost (configurable engineering heuristics, not calibrated global optima):
   - `w_travel = 0.40` ($C_T$: total travel min normalized by $N_{\text{jobs}} \times 60\text{ min}$)
   - `w_sla_risk = 0.30` ($C_S$: mean normalized soft-SLA urgency + soft-breach lateness term)
   - `w_workload = 0.20` ($C_W$: std-dev of service-only shift utilization + normalized overtime; avoids double-counting travel)
   - `w_recovery_change = 0.10` ($C_R$: normalized schedule perturbation vs. baseline; identically `0.0` during initial scheduling)

---

## Integration Contracts for Teammates

### Persistence Integration (Module A)
`app/scheduler/*` has zero database dependencies. FastAPI routes persist runs through the `ScheduleRunRepository` protocol in `app/api/routes/scheduling.py`:
- Replace `app.state.schedule_store` at startup or override `get_schedule_store` via `app.dependency_overrides[get_schedule_store]` with the shared SQLAlchemy/PostgreSQL repository adapter.

### Disruption Recovery Integration (Module D)
Pass current commitments into `generate_schedule(..., existing_assignments=..., unavailability=..., config=...)`:
- `status="completed"`: anchored permanently on its technician and recorded historical timing fields (`departure_min`, `arrival_min`, `planned_start_min`, `completion_min`).
- `status="in_progress"`: anchored on its technician and active timing (`departure_min`, `arrival_min`, `planned_start_min`); if `job.duration_min` grows (e.g. `D03`), `completion_min` updates and downstream stops recalculate automatically.
- `locked=True` (future commitment, e.g. `status="assigned"`): anchored on its technician and `planned_start_min`, while still validated against all applicable future hard constraints (active technician status, shift bounds, unavailability, time windows, max leg travel, and hard SLA deadlines). Conflicts are reported explicitly via `validation_errors` and `is_valid_for_commitment=False` without silently moving the locked assignment.
- `status="cancelled"`: excluded from active demand and frees route capacity (`D04`).
- `status="assigned"` (`locked=False`): preserved when still valid and unaffected, or reassigned cleanly when invalidated by unavailability (`D01`) or urgent `Critical` arrivals (`D02`), penalized by $C_R$ to minimize unnecessary churn.
- Every proposed schedule is gated by `validate_full_schedule` before commitment; failed optimization never overwrites a valid schedule.

