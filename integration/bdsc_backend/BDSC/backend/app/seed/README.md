# DISPATCHGRID — Synthetic Electrician Dataset Specification

## Overview
The seed package (`app/seed/generate_dataset.py` and `app/seed/seed_data.py`) generates a 100% deterministic, repeatable dataset containing **electricians only**:
* **20 Electrician Technicians** (`tech-01` through `tech-20`)
* **100 Electrical Service Jobs** (`job-001` through `job-100`)
* **1 Initial `ACTIVE` Schedule Version (`v1`)** locking the 4 `COMPLETED` and 4 `IN_PROGRESS` morning dispatches so recovery protection can be tested immediately.

All UUIDs are generated deterministically via `uuid.uuid5` and `random.Random(20261030)`. Rerunning `python -m app.seed.seed_data` is idempotent and reconciles the database to exactly 20 technicians and 100 jobs without creating duplicates.

---

## 1. Synthetic Indian Service Zones (Bengaluru Grid)
* `BLR-NORTH-HEBBAL` (`13.0358, 77.5970`)
* `BLR-SOUTH-JAYANAGAR` (`12.9250, 77.5938`)
* `BLR-EAST-WHITEFIELD` (`12.9698, 77.7499`)
* `BLR-WEST-RAJAJINAGAR` (`12.9982, 77.5530`)
* `BLR-CENTRAL-MG-ROAD` (`12.9716, 77.5946`)
* `BLR-SE-KORAMANGALA` (`12.9352, 77.6245`)

---

## 2. Technician Distribution & States
* **Total Electricians**: `20`
* **Availability States Represented**:
  * `AVAILABLE`: 11 technicians
  * `BUSY`: 4 technicians (`tech-01`, `tech-04`, `tech-07`, `tech-11`)
  * `ON_BREAK`: 1 technician (`tech-06`)
  * `OFF_DUTY`: 1 technician (`tech-10`, early shift `06:00–14:00`)
  * `UNAVAILABLE`: 3 technicians (`tech-13` on medical leave; `tech-17` and `tech-20` with `is_active = False`)
* **Time-Bounded Breaks & Unavailable Windows**:
  * Every active technician has scheduled break intervals in `unavailable_windows` (e.g., `12:30–13:00`, `13:00–13:30`, `14:00–15:30` substation calibration) to test time-aware availability checks.

---

## 3. Job Scenarios & Test Cohorts (100 Jobs)
1. **Completed Jobs (`job-001` to `job-004`)**:
   * Status: `COMPLETED`, bound in active Schedule Version `v1`. Protected against any recovery or optimization modification.
2. **In-Progress Jobs (`job-005` to `job-008`)**:
   * Status: `IN_PROGRESS`, bound in active Schedule Version `v1`. Protected against any recovery or optimization modification (`IMMUTABLE_JOB_VIOLATION`).
3. **Standard Multi-Zone Assignable Jobs (`job-009` to `job-080`)**:
   * 72 jobs spanning all 6 electrical job categories (`Fault diagnosis`, `Wiring repair`, `Switch replacement`, `Circuit breaker repair`, `Electrical installation`, `Distribution board maintenance`), priorities (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), and durations (`30–90` minutes).
4. **High-Contention Conflicting Time Windows (`job-081` to `job-092`)**:
   * 12 `HIGH` priority `Distribution board maintenance` jobs all requesting a narrow `10:00–11:15` window simultaneously across zones.
5. **Deliberately Infeasible Jobs (`job-093` to `job-100`)**:
   * `job-093` to `job-096`: Require all 8 electrical skills simultaneously in zones where no active technician holds all 8 skills (`SKILL_MISMATCH`).
   * `job-097` to `job-100`: Request late-night `22:15–23:45` windows when all zone technicians are outside shift hours (`OUTSIDE_SHIFT_HOURS`).

---

## 4. Commands
```bash
# Idempotent seed & reconciliation (safe to run multiple times)
python -m app.seed.seed_data

# Full reset and re-seed
python -m app.seed.seed_data --reset
```
