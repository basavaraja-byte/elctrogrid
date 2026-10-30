# DISPATCHGRID — Intelligent Workforce Scheduling & Recovery Engine (Backend)

Production-grade **FastAPI + SQLAlchemy 2.0 + PostgreSQL** modular monolith backend for **DISPATCHGRID**. Designed for seamless integration with the **Scheduling & Optimization Engine**, **Disruption & Recovery Engine**, and **React + TypeScript Frontend**.

---

## 1. Architecture & Core Features

* **Centralized Hard-Constraint Validation (`app/services/constraint_validator.py`)**:
  Reused across initial scheduling, optimization, recovery proposal generation, candidate ranking, and human approval. Enforces active technician checks, time-aware availability (`AVAILABLE`, `BUSY`, `ON_BREAK`, `UNAVAILABLE`, `OFF_DUTY`), shift bounds, required skills, service zones, appointment windows, non-overlapping intervals with travel buffers, and strict immutability of `COMPLETED` and `IN_PROGRESS` jobs.
* **Schedule Versioning & Human Approval Workflow (`app/services/schedule_service.py`)**:
  Separates the currently `ACTIVE` production schedule from `DRAFT` proposals (`SUPERSEDED` and `REJECTED` versions are preserved for audit and comparison). Disruption `RECOVERY` runs always generate `DRAFT` proposals first and require explicit Operations Manager approval (`POST /api/v1/schedules/{id}/approve`) before activation.
* **Feasible-Only Heuristic Candidate Ranking (`app/services/scoring.py`)**:
  Filters candidates through `ConstraintValidator` first and ranks feasible electricians using documented multi-criteria weights (`travel_time=0.25`, `sla_risk=0.30`, `job_priority=0.15`, `workload_balance=0.15`, `schedule_stability=0.15`) without claiming global optimality.
* **Persisted Schedule Metrics & Before-and-After Diffs (`app/services/metrics_service.py`)**:
  Calculates assigned/unassigned counts, SLA compliance & breaches, total travel time, technician workload distribution (utilization & standard deviation), changed assignments, and hard-constraint violations directly from persisted database rows.
* **Deterministic Electricians-Only Seed Dataset (`app/seed/`)**:
  20 electricians and 100 electrical service jobs across 6 Bengaluru grid zones (`BLR-NORTH-HEBBAL`, `BLR-SOUTH-JAYANAGAR`, `BLR-EAST-WHITEFIELD`, `BLR-WEST-RAJAJINAGAR`, `BLR-CENTRAL-MG-ROAD`, `BLR-SE-KORAMANGALA`) with breaks, unavailable periods, conflicting peak-hour time windows, and deliberately infeasible jobs.

---

## 2. Quick Start (Docker Compose)

```bash
cd backend
docker compose up --build
```
This starts PostgreSQL 16 (`localhost:5432`), runs Alembic migrations (`alembic upgrade head`), seeds the deterministic 20-electrician / 100-job dataset, and launches FastAPI at `http://localhost:8000` (Swagger UI at `http://localhost:8000/docs`).

---

## 3. Local Installation & Environment Setup (Windows / Linux / macOS)

### Prerequisites
* **Python 3.12+** (On Windows: `winget install -e --id Python.Python.3.12`)
* **PostgreSQL 15+** (or SQLite for quick local testing)

### Step 1: Create Virtual Environment & Install Dependencies
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 2: Configure `.env`
```powershell
Copy-Item .env.example .env
```
Edit `.env` if needed to set `DATABASE_URL` (e.g., `postgresql+psycopg://dispatchgrid:dispatchgrid_secret@localhost:5432/dispatchgrid`, or `sqlite:///./dispatchgrid_dev.db` for local zero-config testing).

### Step 3: Run Database Migrations
```powershell
alembic upgrade head
```

### Step 4: Seed the Deterministic Electrician Dataset
```powershell
# Idempotent seed (safe to rerun)
python -m app.seed.seed_data

# Reset and re-seed from scratch
python -m app.seed.seed_data --reset
```

### Step 5: Run the FastAPI Server
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 4. Running the Test Suite

```powershell
cd backend
pytest -v
```
Tests run against an isolated test database (`tests/conftest.py`) and verify:
* Technician & Job CRUD and filtering
* Time-aware availability checks (`AVAILABLE`, `BUSY`, `ON_BREAK`, `UNAVAILABLE`, `OFF_DUTY`)
* Invalid durations, appointment windows, coordinates, and status transitions
* `COMPLETED` and `IN_PROGRESS` immutability protection
* Schedule generation, duplicate `idempotency_key` rejection (`409`), and transaction rollback
* Operations Manager human approval/rejection workflow (`DRAFT` → `ACTIVE` / `SUPERSEDED` / `REJECTED`)
* Feasible-only candidate ranking & documented scoring weights
* Persisted metrics & before-and-after schedule comparison
* Seed dataset repeatability (`20` electricians, `100` jobs)

---

## 5. Documentation Links

* [API Contracts & Shared Scheduler/Recovery Interfaces](docs/API_CONTRACTS.md)
* [Database Schema & Constraints Specification](docs/DATABASE_SCHEMA.md)
* [Synthetic Dataset & Disruption Scenarios Guide](app/seed/README.md)

