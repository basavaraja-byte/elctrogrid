# DISPATCHGRID — API Contracts & Integration Guide

This document defines the canonical REST API contracts, enums, error formats, and shared Python protocols for integrating the **DISPATCHGRID Backend** with the **Scheduling & Optimization Engine**, **Disruption & Recovery Engine**, and **React + TypeScript Frontend**.

---

## 1. Canonical Enumerations (`app/models/enums.py`)

### `AvailabilityStatus`
* `AVAILABLE`: Ready for dispatch within shift hours
* `BUSY`: Currently executing an active job
* `ON_BREAK`: Temporarily on scheduled break
* `UNAVAILABLE`: Out of service (equipment issue, emergency leave, sick)
* `OFF_DUTY`: Outside shift hours

### `JobPriority`
* `LOW`
* `MEDIUM`
* `HIGH`
* `CRITICAL`

### `JobStatus`
* `PENDING`
* `ASSIGNED`
* `IN_PROGRESS` *(Immutable during scheduling/recovery)*
* `COMPLETED` *(Immutable terminal state)*
* `CANCELLED` *(Immutable terminal state)*
* `UNASSIGNED`

### `ScheduleVersionStatus`
* `DRAFT`: Proposed schedule version awaiting human review or activation
* `APPROVED`: Approved by Operations Manager
* `ACTIVE`: The single authoritative active production schedule
* `REJECTED`: Rejected proposal (retained for audit/comparison)
* `SUPERSEDED`: Historical previously-active schedule replaced by a newer active schedule

### `SchedulingRunType`
* `INITIAL`: Baseline schedule generation
* `OPTIMIZATION`: Schedule optimization run
* `RECOVERY`: Disruption recovery run *(Always saved as `DRAFT` first; requires explicit human approval)*

### `SchedulingStrategy`
* `BALANCED`
* `MINIMIZE_TRAVEL`
* `SLA_FIRST`
* `STABILITY_FIRST`

### Canonical `ElectricalSkill` Values
* `Residential wiring`
* `Industrial wiring`
* `Circuit breaker repair`
* `Switch and socket replacement`
* `Electrical fault diagnosis`
* `Distribution board maintenance`
* `Earthing and grounding`
* `Electrical installation`

### Canonical `JobCategory` Values
* `Fault diagnosis`
* `Wiring repair`
* `Switch replacement`
* `Circuit breaker repair`
* `Electrical installation`
* `Distribution board maintenance`

### `CustomerType`
* `INDIVIDUAL`: Residential or individual external client requesting electrical service
* `BUSINESS`: Commercial, industrial, or enterprise external client requesting electrical service

---

## 2. Standard Error Envelope

All error responses (`400`, `404`, `409`, `422`, `500`) follow a strict, uniform JSON structure and never leak stack traces or database credentials:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable explanation",
    "details": [
      {
        "field": "estimated_duration_minutes",
        "issue": "Input should be greater than 0"
      }
    ]
  }
}
```

### Canonical Error Codes
* `VALIDATION_ERROR` (`422` / `400`): Field validation or domain constraint error
* `INVALID_STATE_TRANSITION` (`400`): Disallowed job status transition
* `IMMUTABLE_JOB_VIOLATION` (`400` / `409`): Attempt to modify/reassign an `IN_PROGRESS` or `COMPLETED` job
* `HARD_CONSTRAINT_VIOLATION` (`400` / `409`): Proposed assignment or schedule violates centralized hard constraints
* `SHIFT_POLICY_VIOLATION` (`400` / `422`): Invalid shift start/end times under current overnight shift policy
* `INACTIVE_TECHNICIAN` (`400` / `409`): Attempt to assign work to an inactive technician
* `NOT_FOUND` (`404`): Requested resource does not exist
* `DUPLICATE_IDEMPOTENCY_KEY` (`409`): Scheduling run with this `idempotency_key` already exists
* `ASSIGNMENT_OVERLAP` (`409`): Overlapping assignments for the same technician
* `APPROVAL_REQUIRED` (`400` / `409`): Attempt to auto-activate a `RECOVERY` or disruptive run without human approval
* `INTERNAL_ERROR` (`500`): Sanitized internal server error

---

## 2A. Customer (External Client) Endpoints (`/api/v1/customers`)

A `Customer` represents an external individual or business requesting electrical service (separate from internal employees, technicians, supervisors, or administrators). No passwords or login credentials are stored on `Customer`.

### `POST /api/v1/customers` (`201 Created`)
Automatically generates a unique `customer_code` (`CUST-XXXXXXXX`) and validates `email` (optional/nullable) and `phone_number` (required).
```json
{
  "full_name": "Meera Reddy",
  "email": "facilities@apextechpark.in",
  "phone_number": "+91-80-40901122",
  "alternate_phone_number": "+91-9900112233",
  "customer_type": "BUSINESS",
  "company_name": "Apex Tech Park Pvt Ltd",
  "service_address": "Plot 14, EPIP Zone Phase 2, Whitefield",
  "city": "Bengaluru",
  "state": "Karnataka",
  "postal_code": "560066",
  "latitude": 12.9710,
  "longitude": 77.7510,
  "is_active": true
}
```

### `GET /api/v1/customers` (`200 OK`)
* Query parameters: `customer_type` (`INDIVIDUAL` | `BUSINESS`), `city`, `state`, `is_active`, `skip`, `limit`

### `GET /api/v1/customers/{customer_id}` & `GET /api/v1/customers/by-code/{customer_code}` (`200 OK`)
* Returns a single `CustomerResponse` by UUID or unique `customer_code`.

### `PUT /api/v1/customers/{customer_id}` & `PATCH /api/v1/customers/{customer_id}/status` (`200 OK`)
* Updates customer profile details or toggles `is_active`.

### `GET /api/v1/customers/{customer_id}/jobs` (`200 OK`)
* Lists all electrical service jobs linked to `{customer_id}`.

---

## 3. Job Management Endpoints (`/api/v1/jobs`)

### `POST /api/v1/jobs` (`201 Created`)
**Request Body**:
```json
{
  "customer_name": "Kalyani Motors Workshop",
  "customer_contact": "+91-80-40921001",
  "job_type": "Distribution board maintenance",
  "description": "3-phase main distribution board thermal trip inspection",
  "required_skills": ["Distribution board maintenance", "Electrical fault diagnosis"],
  "priority": "HIGH",
  "latitude": 12.9716,
  "longitude": 77.5946,
  "service_zone": "BLR-CENTRAL-MG-ROAD",
  "estimated_duration_minutes": 90,
  "appointment_window_start": "2026-10-30T09:00:00+05:30",
  "appointment_window_end": "2026-10-30T13:00:00+05:30",
  "sla_deadline": "2026-10-30T14:00:00+05:30"
}
```

### `GET /api/v1/jobs` (`200 OK`)
**Query Parameters**:
* `status` (optional `JobStatus`)
* `priority` (optional `JobPriority`)
* `service_zone` (optional `string`)
* `job_type` (optional `string`)
* `required_skill` (optional `string`)
* `skip` (default `0`), `limit` (default `100`)

### `GET /api/v1/jobs/{job_id}` (`200 OK`)
Returns a single `JobResponse`.

### `PUT /api/v1/jobs/{job_id}` (`200 OK`)
Full update of job attributes. Rejects changes to core scheduling parameters if job is already `COMPLETED` or `IN_PROGRESS`.

### `PATCH /api/v1/jobs/{job_id}/status` (`200 OK`)
**Request Body**:
```json
{
  "status": "IN_PROGRESS",
  "actual_start_time": "2026-10-30T09:35:00+05:30",
  "reason": "Technician arrived on site and started work"
}
```

### `DELETE /api/v1/jobs/{job_id}` (`200 OK`)
Cancels/deletes a job. Rejects deletion if the job is `IN_PROGRESS` or `COMPLETED`.

---

## 4. Technician Management Endpoints (`/api/v1/technicians`)

### `POST /api/v1/technicians` (`201 Created`)
**Request Body**:
```json
{
  "name": "Ramesh Gowda",
  "phone": "+91-9845011223",
  "skills": [
    "Residential wiring",
    "Circuit breaker repair",
    "Distribution board maintenance"
  ],
  "service_zones": ["BLR-SOUTH-JAYANAGAR", "BLR-SE-KORAMANGALA"],
  "latitude": 12.9250,
  "longitude": 77.5938,
  "shift_start": "08:00:00",
  "shift_end": "17:00:00",
  "is_active": true,
  "availability_status": "AVAILABLE",
  "unavailable_windows": [
    {
      "start": "2026-10-30T13:00:00+05:30",
      "end": "2026-10-30T13:30:00+05:30",
      "status": "ON_BREAK",
      "reason": "Scheduled lunch break"
    }
  ]
}
```

### `GET /api/v1/technicians` (`200 OK`)
**Query Parameters**:
* `availability_status` (optional `AvailabilityStatus`: `AVAILABLE`, `BUSY`, `ON_BREAK`, `UNAVAILABLE`, `OFF_DUTY`)
* `skill` (optional `string`)
* `service_zone` (optional `string`)
* `is_active` (optional `boolean`)
* `available_from` (optional `datetime` ISO8601 — triggers time-aware availability check)
* `available_until` (optional `datetime` ISO8601 — triggers time-aware availability check)

### `GET /api/v1/technicians/{technician_id}` (`200 OK`)
Returns a single `TechnicianResponse`.

### `PUT /api/v1/technicians/{technician_id}` (`200 OK`)
Full update of technician details, shift, skills, zones, and `unavailable_windows`.

### `PATCH /api/v1/technicians/{technician_id}/availability` (`200 OK`)
**Request Body**:
```json
{
  "availability_status": "UNAVAILABLE",
  "is_active": true,
  "unavailable_window": {
    "start": "2026-10-30T11:00:00+05:30",
    "end": "2026-10-30T16:00:00+05:30",
    "status": "UNAVAILABLE",
    "reason": "Vehicle breakdown in Whitefield"
  },
  "reason": "Reported van battery failure"
}
```

---

## 5. Shared Scheduling, Recovery, Approval & Metrics Endpoints (`/api/v1/schedules`)

### A. `POST /api/v1/schedules/generate` (`201 Created`)
Generates a new `ScheduleVersion` and `SchedulingRun`.
* Uses the centralized `ConstraintValidator` to verify all assignments and enforce `COMPLETED` / `IN_PROGRESS` recovery protection.
* **Human Approval Policy**: If `run_type == "RECOVERY"` or `auto_activate == false`, the schedule is persisted with `status = "DRAFT"` and does **not** overwrite the currently `ACTIVE` schedule until an Operations Manager approves it. If `run_type == "RECOVERY"` and the caller passes `auto_activate = true`, the endpoint rejects the request with `400 APPROVAL_REQUIRED`.

**Request Body**:
```json
{
  "idempotency_key": "sched-run-2026-10-30-001",
  "run_type": "INITIAL",
  "strategy": "BALANCED",
  "horizon_start": "2026-10-30T08:00:00+05:30",
  "horizon_end": "2026-10-30T20:00:00+05:30",
  "job_ids": null,
  "parent_version_id": null,
  "created_by": "scheduler_service",
  "auto_activate": false,
  "proposed_assignments": null,
  "unassigned_reasons": null
}
```
*(Note: The external Scheduler or Recovery module can either register its `SchedulerEngineProtocol` implementation in Python or pass `proposed_assignments` + `unassigned_reasons` directly in the request payload to persist, validate, version, and audit the schedule).*

**Response Body (`ScheduleGenerationResponse`)**:
```json
{
  "schedule_version": {
    "id": "b6d9f3a2-1111-4444-8888-000000000001",
    "version_number": 2,
    "status": "DRAFT",
    "created_at": "2026-10-30T10:00:00Z",
    "created_by": "recovery_engine",
    "parent_version_id": "b6d9f3a2-1111-4444-8888-000000000000"
  },
  "scheduling_run": {
    "id": "c7e8a1b2-2222-4444-8888-000000000002",
    "schedule_version_id": "b6d9f3a2-1111-4444-8888-000000000001",
    "idempotency_key": "sched-run-2026-10-30-001",
    "run_type": "RECOVERY",
    "strategy": "STABILITY_FIRST",
    "execution_status": "COMPLETED",
    "total_jobs": 120,
    "assigned_jobs": 108,
    "unassigned_jobs": 12,
    "total_travel_minutes": 1840,
    "estimated_late_jobs": 2,
    "execution_time_ms": 65,
    "created_at": "2026-10-30T10:00:00Z"
  },
  "assignments": [
    {
      "id": "a1111111-1111-4444-8888-000000000001",
      "job_id": "d2222222-1111-4444-8888-000000000001",
      "technician_id": "e3333333-1111-4444-8888-000000000001",
      "schedule_version_id": "b6d9f3a2-1111-4444-8888-000000000001",
      "planned_start_time": "2026-10-30T09:00:00+05:30",
      "planned_end_time": "2026-10-30T10:30:00+05:30",
      "estimated_travel_minutes": 18,
      "assignment_status": "PLANNED",
      "assignment_reason": "Feasible score 86.4 (Travel=18m, SLA buffer=210m)",
      "created_at": "2026-10-30T10:00:00Z"
    }
  ],
  "unassigned_jobs": ["d2222222-1111-4444-8888-000000000099"],
  "unassigned_reasons": [
    {
      "job_id": "d2222222-1111-4444-8888-000000000099",
      "reason_code": "NO_MATCHING_SKILL",
      "explanation": "No active technician in BLR-WEST-RAJAJINAGAR holds all required skills"
    }
  ],
  "total_travel_minutes": 1840,
  "assigned_job_count": 108,
  "unassigned_job_count": 12,
  "sla_risk_information": [
    {
      "job_id": "d2222222-1111-4444-8888-000000000001",
      "sla_deadline": "2026-10-30T14:00:00+05:30",
      "planned_end_time": "2026-10-30T10:30:00+05:30",
      "buffer_minutes": 210,
      "risk_level": "LOW",
      "is_late": false
    }
  ]
}
```

### B. `POST /api/v1/schedules/{schedule_id}/approve` (`200 OK`)
Operations Manager approval endpoint to activate a `DRAFT` proposal.
* Re-runs centralized `ConstraintValidator` (including `COMPLETED` and `IN_PROGRESS` protection against the currently `ACTIVE` version).
* Transitions previous `ACTIVE` schedule to `SUPERSEDED` and this version to `ACTIVE`.

**Request Body**:
```json
{
  "approved_by": "ops_manager_anita",
  "reason": "Approved recovery plan after Whitefield technician breakdown; only 3 jobs reassigned"
}
```

### C. `POST /api/v1/schedules/{schedule_id}/reject` (`200 OK`)
Operations Manager rejection endpoint for a `DRAFT` proposal. Leaves the currently `ACTIVE` schedule unchanged.

**Request Body**:
```json
{
  "rejected_by": "ops_manager_anita",
  "reason": "Too many reassignments in Koramangala zone"
}
```

### D. `GET /api/v1/schedules/current` (`200 OK`)
Returns the currently `ACTIVE` `ScheduleGenerationResponse` (or `404 NOT_FOUND` if no schedule is currently active).

### E. `GET /api/v1/schedules/{schedule_id}` (`200 OK`)
Returns the full `ScheduleGenerationResponse` for any historical, draft, rejected, or active schedule version.

### F. `GET /api/v1/schedules/{schedule_id}/metrics` (`200 OK`)
Computes actual persisted metrics for `{schedule_id}`:
* `assigned_jobs_count`, `unassigned_jobs_count`
* `sla_compliant_count`, `sla_at_risk_count`, `sla_breached_count`, `sla_compliance_rate_pct`
* `total_estimated_travel_minutes`
* `technician_workload_distribution` (per-technician utilization & standard deviation)
* `hard_constraint_violations_count` & `hard_constraint_violations`

### G. `GET /api/v1/schedules/{schedule_id}/compare/{other_schedule_id}` (`200 OK`)
Computes before-and-after comparison between `{schedule_id}` (base) and `{other_schedule_id}` (target):
* `base_metrics` & `target_metrics`
* `deltas` (assigned jobs, unassigned jobs, SLA compliance %, travel minutes, workload std dev, constraint violations)
* `changed_assignments_count`
* `assignment_changes` (`UNCHANGED`, `REASSIGNED_TECHNICIAN`, `TIME_SHIFTED`, `NEWLY_ASSIGNED`, `NEWLY_UNASSIGNED`)

### H. `POST /api/v1/schedules/rank-candidates` (`200 OK`)
Evaluates all technicians for a given `job_id` and planned time window using `ConstraintValidator` first, then ranks **only feasible technicians** using the documented multi-criteria heuristic weights:
* Travel time weight: `0.25`
* SLA risk weight: `0.30`
* Job priority weight: `0.15`
* Workload balance weight: `0.15`
* Schedule stability weight: `0.15`
*(Explicitly returns `"is_globally_optimal": false` and `scoring_weights` in the response).*

