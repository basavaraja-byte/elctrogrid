"""Principled synthetic historical dataset generator for DispatchGrid AI.

Generates reproducible historical electrical service logs with realistic domain physics:
- Job complexity & duration distributions tailored to electrical maintenance trades
- Travel times across urban zones (Mysuru)
- SLA deadlines and realistic delay mechanics
- Workload-induced schedule disruptions
All records are strictly tagged with data_provenance="SYNTHETIC_AUGMENTED".
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.ai.config import ai_config

JOB_TYPES = [
    "residential_wiring",
    "commercial_wiring",
    "safety_inspection",
    "ev_charger_installation",
    "fault_diagnosis",
    "distribution_panel_repair",
    "electrical_installation",
    "circuit_breaker_repair",
    "switch_replacement",
]

PRIORITIES = ["Low", "Normal", "High", "Critical"]
PRIORITY_WEIGHTS = [0.15, 0.55, 0.20, 0.10]

ZONES = ["Central", "North", "South", "East", "West"]
ZONE_WEIGHTS = [0.30, 0.20, 0.20, 0.15, 0.15]

CUSTOMER_TYPES = ["individual", "commercial"]
CUSTOMER_WEIGHTS = [0.70, 0.30]

# Baseline physical duration parameters (minutes)
BASE_DURATION_PARAMS: dict[str, tuple[float, float]] = {
    # (mean_min, std_min)
    "residential_wiring": (125.0, 25.0),
    "commercial_wiring": (160.0, 35.0),
    "safety_inspection": (40.0, 10.0),
    "ev_charger_installation": (130.0, 20.0),
    "fault_diagnosis": (60.0, 25.0),
    "distribution_panel_repair": (120.0, 30.0),
    "electrical_installation": (95.0, 20.0),
    "circuit_breaker_repair": (55.0, 15.0),
    "switch_replacement": (35.0, 8.0),
}


def generate_synthetic_historical_dataset(
    n_samples: int = 1500,
    random_seed: int = ai_config.random_seed,
) -> pd.DataFrame:
    """Generate a high-quality historical electrical service dataset for ML training.

    Ensures zero data leakage: inputs reflect only pre-dispatch information.
    Target labels (actual_duration_min, sla_delayed, disruption_occurred) are
    ground-truth outcomes computed from simulated execution physics.
    """
    rng = np.random.default_rng(random_seed)

    records = []
    # 20 simulated technicians with experience rating 1 to 5
    tech_experience = {f"TECH-{i:03d}": rng.integers(1, 6) for i in range(1, 21)}

    for i in range(1, n_samples + 1):
        job_id = f"HIST-JOB-{i:04d}"
        job_type = rng.choice(JOB_TYPES)
        priority = rng.choice(PRIORITIES, p=PRIORITY_WEIGHTS)
        zone = rng.choice(ZONES, p=ZONE_WEIGHTS)
        cust_type = rng.choice(CUSTOMER_TYPES, p=CUSTOMER_WEIGHTS)

        # Skill requirement complexity
        if job_type in ["commercial_wiring", "distribution_panel_repair", "ev_charger_installation"]:
            skill_count = rng.integers(2, 5)
        elif job_type in ["residential_wiring", "fault_diagnosis", "electrical_installation"]:
            skill_count = rng.integers(1, 3)
        else:
            skill_count = 1

        # Appointment window (e.g. between 08:00=480 min and 17:00=1020 min)
        start_hour_min = rng.choice([480, 540, 600, 660, 720, 780, 840])
        window_span = rng.choice([60, 90, 120, 180])
        window_end_min = start_hour_min + window_span

        # SLA deadline based on priority
        if priority == "Critical":
            sla_slack = rng.choice([60, 90, 120])
        elif priority == "High":
            sla_slack = rng.choice([120, 180, 240])
        elif priority == "Normal":
            sla_slack = rng.choice([240, 360, 480])
        else:  # Low
            sla_slack = rng.choice([360, 600, 720])
        sla_deadline_min = start_hour_min + sla_slack

        # Customer-estimated duration
        base_mean, base_std = BASE_DURATION_PARAMS[job_type]
        est_duration_min = float(np.round(base_mean + rng.normal(0, base_std * 0.3)))
        est_duration_min = max(20.0, est_duration_min)

        # Simulated assignment & execution mechanics
        assigned_tech = f"TECH-{rng.integers(1, 21):03d}"
        tech_exp = tech_experience[assigned_tech]
        tech_workload_hours = float(np.round(rng.uniform(3.0, 9.5), 1))
        tight_buffers = int(rng.binomial(3, 0.3))
        est_travel_min = float(np.round(rng.uniform(10.0, 40.0), 1))

        # Actual duration generation with physical factors:
        # 1. Commercial properties add ~15% complexity
        # 2. Skill count adds ~5% per extra skill
        # 3. Experienced technicians execute ~4% faster per star
        # 4. Critical priority has urgency factor (~8% faster due to focused protocol)
        # 5. Stochastic real-world physical variation (e.g. corroded wiring, conduit blockages)
        commercial_factor = 1.15 if cust_type == "commercial" else 1.0
        skill_factor = 1.0 + (skill_count - 1) * 0.05
        experience_factor = 1.12 - (tech_exp * 0.04)
        priority_factor = 0.92 if priority == "Critical" else (0.96 if priority == "High" else 1.0)

        # Base physical calculation
        expected_actual = (
            base_mean
            * commercial_factor
            * skill_factor
            * experience_factor
            * priority_factor
        )
        actual_noise = rng.normal(0, base_std * 0.8)
        # 8% chance of anomalous delay (hidden obstacle, missing part)
        if rng.random() < 0.08:
            actual_noise += rng.uniform(30.0, 75.0)

        actual_duration_min = float(np.round(max(15.0, expected_actual + actual_noise), 1))

        # Planned vs actual dispatch times
        planned_start_min = start_hour_min + int(rng.uniform(0, 30))
        # Delays due to travel congestion or prior job overrun
        departure_delay = est_travel_min * (0.2 if tech_workload_hours > 7.5 else 0.0)
        actual_start_min = planned_start_min + departure_delay
        actual_completion_min = actual_start_min + actual_duration_min

        # Target 2: SLA Delayed outcome
        sla_delayed = int(actual_completion_min > sla_deadline_min)

        # Target 3: Disruption outcome
        # Overwork, tight buffers, and major duration overruns trigger disruption events
        overrun_ratio = actual_duration_min / est_duration_min
        disruption_risk_score = (
            (0.35 if tech_workload_hours > 8.0 else 0.0)
            + (0.30 if tight_buffers >= 2 else 0.0)
            + (0.35 if overrun_ratio > 1.35 else 0.0)
            + (0.15 if sla_delayed else 0.0)
        )
        disruption_occurred = int(rng.random() < min(0.90, disruption_risk_score))

        # Day of week (0=Mon to 6=Sun) and hour of day
        day_of_week = int(rng.integers(0, 7))
        hour_of_day = int(start_hour_min // 60)

        records.append({
            "job_id": job_id,
            "job_type": job_type,
            "priority": priority,
            "service_zone": zone,
            "customer_type": cust_type,
            "skill_count": skill_count,
            "window_start_min": start_hour_min,
            "window_end_min": window_end_min,
            "window_span_min": window_span,
            "sla_deadline_min": sla_deadline_min,
            "sla_slack_min": sla_deadline_min - start_hour_min,
            "estimated_duration_min": est_duration_min,
            "estimated_travel_min": est_travel_min,
            "assigned_technician_id": assigned_tech,
            "technician_experience": tech_exp,
            "technician_workload_hours": tech_workload_hours,
            "tight_buffer_count": tight_buffers,
            "day_of_week": day_of_week,
            "hour_of_day": hour_of_day,
            # Ground-truth targets
            "actual_duration_min": actual_duration_min,
            "actual_start_min": actual_start_min,
            "actual_completion_min": actual_completion_min,
            "sla_delayed": sla_delayed,
            "disruption_occurred": disruption_occurred,
            # Provenance
            "data_provenance": "SYNTHETIC_AUGMENTED",
        })

    df = pd.DataFrame(records)
    return df

