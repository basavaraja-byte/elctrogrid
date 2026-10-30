# DispatchGrid — AI Data Dictionary & Provenance

This document specifies all data fields, sources, and provenance standards used throughout DispatchGrid Machine Learning pipelines.

---

## 1. Data Provenance Standards

In enterprise ML, mixing fictional benchmark coordinates with real GPS telemetry or claiming synthetic data is real customer history damages credibility. DispatchGrid enforces three strict provenance tiers:

| Provenance Tag | Source | Usage & Limitations |
| :--- | :--- | :--- |
| `SYNTHETIC_BENCHMARK` | Original CSV files (`backend/data/*.csv`) | Baseline benchmark for scheduling algorithms |
| `OPERATIONAL_DB` | SQLite / PostgreSQL `dispatchgrid.db` | Live operational state (seeded + customer created) |
| `SYNTHETIC_AUGMENTED` | Physics-based generator (`synthetic_generator.py`) | Statistical augmentation for reproducible ML model training |

---

## 2. Feature Definitions

### Pre-Dispatch Features (Available at Booking / Scheduling Time)

| Feature Name | Data Type | Permitted Values / Units | Description |
| :--- | :--- | :--- | :--- |
| `job_id` | String | e.g. `JOB-001`, `HIST-001` | Unique ticket identifier |
| `job_type` | Categorical | `residential_wiring`, `commercial_wiring`, `safety_inspection`, `ev_charger_installation`, `fault_diagnosis`, `distribution_panel_repair`, `electrical_installation`, `circuit_breaker_repair`, `switch_replacement` | Specific electrical maintenance trade category |
| `priority` | Categorical | `Low`, `Normal`, `High`, `Critical` | Urgency tier governing SLA deadlines |
| `service_zone` | Categorical | `Central`, `North`, `South`, `East`, `West` | Urban service quadrant (Mysuru) |
| `customer_type` | Categorical | `individual`, `commercial` | Customer category (commercial adds complexity) |
| `skill_count` | Integer | $1 \le x \le 5$ | Number of certified skills required |
| `window_span_min` | Integer | Minutes (e.g. 60, 120, 180) | Duration of customer appointment window |
| `estimated_duration_min` | Float | Minutes ($20 \le x \le 360$) | Initial customer or dispatcher duration guess |
| `estimated_travel_min` | Float | Minutes ($10 \le x \le 45$) | Estimated transit time from technician location |
| `sla_slack_min` | Integer | Minutes | Time available from window start to SLA deadline |
| `duration_to_slack_ratio`| Float | Ratio ($\ge 0.0$) | $\frac{\text{predicted\_duration}}{\text{sla\_slack}}$ |
| `buffer_slack_min` | Float | Minutes | $\text{slack} - (\text{duration} + \text{travel})$ |
| `technician_workload_hours`| Float | Hours ($0.0 \le x \le 12.0$) | Cumulative hours already assigned to technician today |
| `tight_buffer_count` | Integer | Count ($\ge 0$) | Number of consecutive jobs with $<15$m transit buffer |
| `overwork_index` | Float | Hours ($\ge 0.0$) | $\max(0, \text{workload\_hours} - 8.0)$ |

### Ground-Truth Target Labels (Only Generated After Execution)

| Target Label | Data Type | Meaning | Used in Model |
| :--- | :--- | :--- | :--- |
| `actual_duration_min` | Float (Continuous) | Physical time spent on site | **Model 1 (Duration Regressor)** |
| `sla_delayed` | Binary ($0$ or $1$) | $1$ if completed after SLA deadline, else $0$ | **Model 2 (SLA Delay Classifier)** |
| `daily_job_count` | Float (Discrete) | Total jobs received in zone on target day | **Model 3 (Demand Forecaster)** |
| `disruption_occurred` | Binary ($0$ or $1$) | $1$ if schedule overrun/delay cascaded, else $0$ | **Model 4 (Disruption Classifier)** |

---

## 3. Data Leakage Prevention Guarantees

- **No Future Timestamps as Inputs**: Completion timestamps (`actual_completion_time`), technician feedback ratings, and post-work notes are **never** passed into feature engineering pipelines.
- **Strictly Chronological Splits**: Time-series demand forecasting splits training and test partitions by calendar date, ensuring models never train on "future" customer request patterns.

