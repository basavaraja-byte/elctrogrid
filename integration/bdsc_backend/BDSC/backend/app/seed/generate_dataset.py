"""Deterministic synthetic dataset generator — Electricians Only (Mandatory Addition #8).

Generates:
- 20 Electricians across 6 Bengaluru grid zones with varied shifts, skills, breaks,
  unavailable windows, and statuses (AVAILABLE, BUSY, ON_BREAK, UNAVAILABLE, OFF_DUTY,
  plus 2 inactive technicians).
- 100 Electrical Service Jobs across 6 electrical job categories with varied priorities,
  durations, appointment windows, SLA deadlines, 4 COMPLETED jobs, 4 IN_PROGRESS jobs,
  conflicting time-window clusters, and 8 deliberately infeasible jobs.
"""

from datetime import datetime, time, timedelta, timezone
import random
from typing import Any
import uuid

from app.models.enums import (
    AvailabilityStatus,
    CustomerType,
    ElectricalSkill,
    JobCategory,
    JobPriority,
    JobStatus,
)

# Deterministic namespace UUID so rerunning always produces identical UUIDs
SEED_NAMESPACE = uuid.UUID("91f8c300-74f7-467a-be91-4c02be95dabf")

# Fixed reference date in IST (UTC+05:30): 2026-10-30
IST = timezone(timedelta(hours=5, minutes=30))
BASE_DATE = datetime(2026, 10, 30, 0, 0, 0, tzinfo=IST)

BENGALURU_ZONES: dict[str, dict[str, Any]] = {
    "BLR-NORTH-HEBBAL": {
        "center_lat": 13.0358,
        "center_lon": 77.5970,
        "locality_prefix": "Hebbal Industrial & Tech Park",
    },
    "BLR-SOUTH-JAYANAGAR": {
        "center_lat": 12.9250,
        "center_lon": 77.5938,
        "locality_prefix": "Jayanagar 4th Block Grid",
    },
    "BLR-EAST-WHITEFIELD": {
        "center_lat": 12.9698,
        "center_lon": 77.7499,
        "locality_prefix": "Whitefield EPIP Phase-2",
    },
    "BLR-WEST-RAJAJINAGAR": {
        "center_lat": 12.9982,
        "center_lon": 77.5530,
        "locality_prefix": "Rajajinagar Industrial Estate",
    },
    "BLR-CENTRAL-MG-ROAD": {
        "center_lat": 12.9716,
        "center_lon": 77.5946,
        "locality_prefix": "Central Commercial Corridor",
    },
    "BLR-SE-KORAMANGALA": {
        "center_lat": 12.9352,
        "center_lon": 77.6245,
        "locality_prefix": "Koramangala Commercial Hub",
    },
}

CATEGORY_TO_REQUIRED_SKILLS: dict[str, list[str]] = {
    JobCategory.FAULT_DIAGNOSIS.value: [
        ElectricalSkill.ELECTRICAL_FAULT_DIAGNOSIS.value,
    ],
    JobCategory.WIRING_REPAIR.value: [
        ElectricalSkill.RESIDENTIAL_WIRING.value,
    ],
    JobCategory.SWITCH_REPLACEMENT.value: [
        ElectricalSkill.SWITCH_AND_SOCKET_REPLACEMENT.value,
    ],
    JobCategory.CIRCUIT_BREAKER_REPAIR.value: [
        ElectricalSkill.CIRCUIT_BREAKER_REPAIR.value,
    ],
    JobCategory.ELECTRICAL_INSTALLATION.value: [
        ElectricalSkill.ELECTRICAL_INSTALLATION.value,
        ElectricalSkill.EARTHING_AND_GROUNDING.value,
    ],
    JobCategory.DISTRIBUTION_BOARD_MAINTENANCE.value: [
        ElectricalSkill.DISTRIBUTION_BOARD_MAINTENANCE.value,
        ElectricalSkill.CIRCUIT_BREAKER_REPAIR.value,
    ],
}


def _det_uuid(key: str) -> uuid.UUID:
    """Return a deterministic UUIDv5 for a given string key."""
    return uuid.uuid5(SEED_NAMESPACE, key)


def _ist_dt(hour: int, minute: int = 0) -> datetime:
    """Return a timezone-aware datetime on BASE_DATE in IST normalized to UTC."""
    return datetime(2026, 10, 30, hour, minute, 0, tzinfo=IST).astimezone(timezone.utc)


def generate_synthetic_dataset() -> dict[str, Any]:
    """Generate the complete deterministic dataset of exactly 20 electricians and 100 electrical service jobs."""
    rng = random.Random(20261030)

    zone_keys = list(BENGALURU_ZONES.keys())
    all_skills = [s.value for s in ElectricalSkill]

    technician_specs: list[dict[str, Any]] = [
        # 1-3: BLR-NORTH-HEBBAL
        {
            "key": "tech-01",
            "name": "Arjun Vishwakarma",
            "zones": ["BLR-NORTH-HEBBAL", "BLR-CENTRAL-MG-ROAD"],
            "skills": [
                ElectricalSkill.RESIDENTIAL_WIRING.value,
                ElectricalSkill.ELECTRICAL_FAULT_DIAGNOSIS.value,
                ElectricalSkill.CIRCUIT_BREAKER_REPAIR.value,
                ElectricalSkill.SWITCH_AND_SOCKET_REPLACEMENT.value,
            ],
            "shift": (time(8, 0), time(17, 0)),
            "status": AvailabilityStatus.BUSY.value,
            "is_active": True,
            "breaks": [(_ist_dt(13, 0), _ist_dt(13, 30), "ON_BREAK", "Lunch break")],
        },
        {
            "key": "tech-02",
            "name": "Kiran Kumar Acharya",
            "zones": ["BLR-NORTH-HEBBAL"],
            "skills": [
                ElectricalSkill.INDUSTRIAL_WIRING.value,
                ElectricalSkill.DISTRIBUTION_BOARD_MAINTENANCE.value,
                ElectricalSkill.CIRCUIT_BREAKER_REPAIR.value,
                ElectricalSkill.EARTHING_AND_GROUNDING.value,
            ],
            "shift": (time(7, 0), time(16, 0)),
            "status": AvailabilityStatus.AVAILABLE.value,
            "is_active": True,
            "breaks": [(_ist_dt(12, 30), _ist_dt(13, 0), "ON_BREAK", "Midday meal break")],
        },
        {
            "key": "tech-03",
            "name": "Prashanth Hegde",
            "zones": ["BLR-NORTH-HEBBAL", "BLR-WEST-RAJAJINAGAR"],
            "skills": [
                ElectricalSkill.ELECTRICAL_INSTALLATION.value,
                ElectricalSkill.EARTHING_AND_GROUNDING.value,
                ElectricalSkill.RESIDENTIAL_WIRING.value,
                ElectricalSkill.SWITCH_AND_SOCKET_REPLACEMENT.value,
            ],
            "shift": (time(9, 0), time(18, 0)),
            "status": AvailabilityStatus.AVAILABLE.value,
            "is_active": True,
            "breaks": [(_ist_dt(13, 30), _ist_dt(14, 0), "ON_BREAK", "Lunch break")],
        },
        # 4-6: BLR-SOUTH-JAYANAGAR
        {
            "key": "tech-04",
            "name": "Ramesh Gowda",
            "zones": ["BLR-SOUTH-JAYANAGAR", "BLR-SE-KORAMANGALA"],
            "skills": [
                ElectricalSkill.RESIDENTIAL_WIRING.value,
                ElectricalSkill.CIRCUIT_BREAKER_REPAIR.value,
                ElectricalSkill.DISTRIBUTION_BOARD_MAINTENANCE.value,
                ElectricalSkill.ELECTRICAL_FAULT_DIAGNOSIS.value,
            ],
            "shift": (time(8, 0), time(17, 0)),
            "status": AvailabilityStatus.BUSY.value,
            "is_active": True,
            "breaks": [(_ist_dt(13, 0), _ist_dt(13, 30), "ON_BREAK", "Lunch break")],
        },
        {
            "key": "tech-05",
            "name": "Suresh Babu",
            "zones": ["BLR-SOUTH-JAYANAGAR"],
            "skills": [
                ElectricalSkill.SWITCH_AND_SOCKET_REPLACEMENT.value,
                ElectricalSkill.RESIDENTIAL_WIRING.value,
                ElectricalSkill.ELECTRICAL_INSTALLATION.value,
                ElectricalSkill.EARTHING_AND_GROUNDING.value,
            ],
            "shift": (time(8, 0), time(17, 0)),
            "status": AvailabilityStatus.AVAILABLE.value,
            "is_active": True,
            "breaks": [(_ist_dt(12, 30), _ist_dt(13, 0), "ON_BREAK", "Lunch break")],
        },
        {
            "key": "tech-06",
            "name": "Mahesh Kulkarni",
            "zones": ["BLR-SOUTH-JAYANAGAR", "BLR-CENTRAL-MG-ROAD"],
            "skills": [
                ElectricalSkill.INDUSTRIAL_WIRING.value,
                ElectricalSkill.DISTRIBUTION_BOARD_MAINTENANCE.value,
                ElectricalSkill.CIRCUIT_BREAKER_REPAIR.value,
                ElectricalSkill.ELECTRICAL_FAULT_DIAGNOSIS.value,
            ],
            "shift": (time(10, 0), time(19, 0)),
            "status": AvailabilityStatus.ON_BREAK.value,
            "is_active": True,
            "breaks": [(_ist_dt(14, 0), _ist_dt(14, 45), "ON_BREAK", "Scheduled afternoon break")],
        },
        # 7-10: BLR-EAST-WHITEFIELD
        {
            "key": "tech-07",
            "name": "Venkatesh Iyer",
            "zones": ["BLR-EAST-WHITEFIELD", "BLR-SE-KORAMANGALA"],
            "skills": [
                ElectricalSkill.INDUSTRIAL_WIRING.value,
                ElectricalSkill.DISTRIBUTION_BOARD_MAINTENANCE.value,
                ElectricalSkill.CIRCUIT_BREAKER_REPAIR.value,
                ElectricalSkill.ELECTRICAL_FAULT_DIAGNOSIS.value,
            ],
            "shift": (time(8, 0), time(17, 0)),
            "status": AvailabilityStatus.BUSY.value,
            "is_active": True,
            "breaks": [(_ist_dt(13, 0), _ist_dt(13, 30), "ON_BREAK", "Lunch break")],
        },
        {
            "key": "tech-08",
            "name": "Anand Raj",
            "zones": ["BLR-EAST-WHITEFIELD"],
            "skills": [
                ElectricalSkill.RESIDENTIAL_WIRING.value,
                ElectricalSkill.SWITCH_AND_SOCKET_REPLACEMENT.value,
                ElectricalSkill.ELECTRICAL_INSTALLATION.value,
                ElectricalSkill.EARTHING_AND_GROUNDING.value,
            ],
            "shift": (time(8, 0), time(17, 0)),
            "status": AvailabilityStatus.AVAILABLE.value,
            "is_active": True,
            "breaks": [(_ist_dt(12, 30), _ist_dt(13, 0), "ON_BREAK", "Lunch break")],
        },
        {
            "key": "tech-09",
            "name": "Harish Chandra",
            "zones": ["BLR-EAST-WHITEFIELD"],
            "skills": [
                ElectricalSkill.ELECTRICAL_FAULT_DIAGNOSIS.value,
                ElectricalSkill.CIRCUIT_BREAKER_REPAIR.value,
                ElectricalSkill.RESIDENTIAL_WIRING.value,
            ],
            "shift": (time(9, 0), time(18, 0)),
            "status": AvailabilityStatus.AVAILABLE.value,
            "is_active": True,
            "breaks": [
                (
                    _ist_dt(14, 0),
                    _ist_dt(15, 30),
                    "UNAVAILABLE",
                    "Substations safety calibration",
                )
            ],
        },
        {
            "key": "tech-10",
            "name": "Manjunath Swamy",
            "zones": ["BLR-EAST-WHITEFIELD"],
            "skills": all_skills,
            "shift": (time(6, 0), time(14, 0)),
            "status": AvailabilityStatus.OFF_DUTY.value,
            "is_active": True,
            "breaks": [(_ist_dt(10, 0), _ist_dt(10, 30), "ON_BREAK", "Breakfast break")],
        },
        # 11-13: BLR-WEST-RAJAJINAGAR
        {
            "key": "tech-11",
            "name": "Girish Naik",
            "zones": ["BLR-WEST-RAJAJINAGAR", "BLR-NORTH-HEBBAL"],
            "skills": [
                ElectricalSkill.INDUSTRIAL_WIRING.value,
                ElectricalSkill.DISTRIBUTION_BOARD_MAINTENANCE.value,
                ElectricalSkill.CIRCUIT_BREAKER_REPAIR.value,
                ElectricalSkill.ELECTRICAL_FAULT_DIAGNOSIS.value,
            ],
            "shift": (time(8, 0), time(17, 0)),
            "status": AvailabilityStatus.BUSY.value,
            "is_active": True,
            "breaks": [(_ist_dt(13, 0), _ist_dt(13, 30), "ON_BREAK", "Lunch break")],
        },
        {
            "key": "tech-12",
            "name": "Chetan Deshpande",
            "zones": ["BLR-WEST-RAJAJINAGAR"],
            "skills": [
                ElectricalSkill.RESIDENTIAL_WIRING.value,
                ElectricalSkill.SWITCH_AND_SOCKET_REPLACEMENT.value,
                ElectricalSkill.ELECTRICAL_INSTALLATION.value,
                ElectricalSkill.EARTHING_AND_GROUNDING.value,
            ],
            "shift": (time(8, 0), time(17, 0)),
            "status": AvailabilityStatus.AVAILABLE.value,
            "is_active": True,
            "breaks": [(_ist_dt(12, 30), _ist_dt(13, 0), "ON_BREAK", "Lunch break")],
        },
        {
            "key": "tech-13",
            "name": "Vinod Kumar",
            "zones": ["BLR-WEST-RAJAJINAGAR"],
            "skills": [
                ElectricalSkill.INDUSTRIAL_WIRING.value,
                ElectricalSkill.EARTHING_AND_GROUNDING.value,
            ],
            "shift": (time(8, 0), time(17, 0)),
            "status": AvailabilityStatus.UNAVAILABLE.value,
            "is_active": True,
            "breaks": [
                (
                    _ist_dt(8, 0),
                    _ist_dt(17, 0),
                    "UNAVAILABLE",
                    "Medical leave — unavailable all shift",
                )
            ],
        },
        # 14-17: BLR-CENTRAL-MG-ROAD
        {
            "key": "tech-14",
            "name": "Raghavendra Rao",
            "zones": ["BLR-CENTRAL-MG-ROAD", "BLR-SOUTH-JAYANAGAR"],
            "skills": [
                ElectricalSkill.DISTRIBUTION_BOARD_MAINTENANCE.value,
                ElectricalSkill.CIRCUIT_BREAKER_REPAIR.value,
                ElectricalSkill.ELECTRICAL_FAULT_DIAGNOSIS.value,
                ElectricalSkill.RESIDENTIAL_WIRING.value,
            ],
            "shift": (time(8, 0), time(17, 0)),
            "status": AvailabilityStatus.AVAILABLE.value,
            "is_active": True,
            "breaks": [(_ist_dt(13, 0), _ist_dt(13, 30), "ON_BREAK", "Lunch break")],
        },
        {
            "key": "tech-15",
            "name": "Syed Irfan",
            "zones": ["BLR-CENTRAL-MG-ROAD", "BLR-EAST-WHITEFIELD"],
            "skills": [
                ElectricalSkill.ELECTRICAL_INSTALLATION.value,
                ElectricalSkill.EARTHING_AND_GROUNDING.value,
                ElectricalSkill.SWITCH_AND_SOCKET_REPLACEMENT.value,
                ElectricalSkill.RESIDENTIAL_WIRING.value,
            ],
            "shift": (time(8, 0), time(17, 0)),
            "status": AvailabilityStatus.AVAILABLE.value,
            "is_active": True,
            "breaks": [(_ist_dt(12, 30), _ist_dt(13, 0), "ON_BREAK", "Lunch break")],
        },
        {
            "key": "tech-16",
            "name": "Karthik Subramanian",
            "zones": ["BLR-CENTRAL-MG-ROAD"],
            "skills": [
                ElectricalSkill.INDUSTRIAL_WIRING.value,
                ElectricalSkill.ELECTRICAL_FAULT_DIAGNOSIS.value,
                ElectricalSkill.CIRCUIT_BREAKER_REPAIR.value,
                ElectricalSkill.SWITCH_AND_SOCKET_REPLACEMENT.value,
            ],
            "shift": (time(11, 0), time(20, 0)),
            "status": AvailabilityStatus.AVAILABLE.value,
            "is_active": True,
            "breaks": [(_ist_dt(15, 0), _ist_dt(15, 30), "ON_BREAK", "Lunch break")],
        },
        {
            "key": "tech-17",
            "name": "Bharath Bhushan",
            "zones": ["BLR-CENTRAL-MG-ROAD"],
            "skills": all_skills,
            "shift": (time(8, 0), time(17, 0)),
            "status": AvailabilityStatus.UNAVAILABLE.value,
            "is_active": False,  # Inactive technician test case
            "breaks": [],
        },
        # 18-20: BLR-SE-KORAMANGALA
        {
            "key": "tech-18",
            "name": "Nagaraj Patil",
            "zones": ["BLR-SE-KORAMANGALA", "BLR-SOUTH-JAYANAGAR"],
            "skills": [
                ElectricalSkill.RESIDENTIAL_WIRING.value,
                ElectricalSkill.SWITCH_AND_SOCKET_REPLACEMENT.value,
                ElectricalSkill.CIRCUIT_BREAKER_REPAIR.value,
                ElectricalSkill.ELECTRICAL_FAULT_DIAGNOSIS.value,
            ],
            "shift": (time(8, 0), time(17, 0)),
            "status": AvailabilityStatus.AVAILABLE.value,
            "is_active": True,
            "breaks": [(_ist_dt(13, 0), _ist_dt(13, 30), "ON_BREAK", "Lunch break")],
        },
        {
            "key": "tech-19",
            "name": "Shashank Joshi",
            "zones": ["BLR-SE-KORAMANGALA", "BLR-EAST-WHITEFIELD"],
            "skills": [
                ElectricalSkill.DISTRIBUTION_BOARD_MAINTENANCE.value,
                ElectricalSkill.CIRCUIT_BREAKER_REPAIR.value,
                ElectricalSkill.ELECTRICAL_INSTALLATION.value,
                ElectricalSkill.EARTHING_AND_GROUNDING.value,
            ],
            "shift": (time(9, 0), time(18, 0)),
            "status": AvailabilityStatus.AVAILABLE.value,
            "is_active": True,
            "breaks": [(_ist_dt(13, 30), _ist_dt(14, 0), "ON_BREAK", "Lunch break")],
        },
        {
            "key": "tech-20",
            "name": "Darshan Srinivas",
            "zones": ["BLR-SE-KORAMANGALA"],
            "skills": [
                ElectricalSkill.SWITCH_AND_SOCKET_REPLACEMENT.value,
                ElectricalSkill.RESIDENTIAL_WIRING.value,
            ],
            "shift": (time(8, 0), time(17, 0)),
            "status": AvailabilityStatus.UNAVAILABLE.value,
            "is_active": False,  # Second inactive technician
            "breaks": [],
        },
    ]

    technicians_data: list[dict[str, Any]] = []
    for idx, spec in enumerate(technician_specs, start=1):
        primary_zone = spec["zones"][0]
        z_meta = BENGALURU_ZONES[primary_zone]
        lat_offset = rng.uniform(-0.015, 0.015)
        lon_offset = rng.uniform(-0.015, 0.015)
        tech_id = _det_uuid(spec["key"])

        windows = [
            {
                "start": w[0].isoformat(),
                "end": w[1].isoformat(),
                "status": w[2],
                "reason": w[3],
            }
            for w in spec["breaks"]
        ]

        technicians_data.append(
            {
                "id": tech_id,
                "name": spec["name"][0].upper() + spec["name"][1:],
                "phone": f"+91-98450{10000 + idx:05d}",
                "skills": spec["skills"],
                "service_zones": spec["zones"],
                "latitude": round(z_meta["center_lat"] + lat_offset, 6),
                "longitude": round(z_meta["center_lon"] + lon_offset, 6),
                "shift_start": spec["shift"][0],
                "shift_end": spec["shift"][1],
                "is_active": spec["is_active"],
                "availability_status": spec["status"],
                "unavailable_windows": windows,
            }
        )

    # Generate exactly 100 electrical service jobs:
    # - Jobs 1..4: COMPLETED jobs (locked in initial active schedule)
    # - Jobs 5..8: IN_PROGRESS jobs (locked in initial active schedule)
    # - Jobs 9..80: Standard & overlapping-window assignable electrical jobs across all 6 zones (72 jobs)
    # - Jobs 81..92: High-contention conflicting time-window jobs (tight 60-min windows at 10:00-11:15) (12 jobs)
    # - Jobs 93..100: Deliberately infeasible jobs (impossible multi-skill combo in zone or out-of-shift window) (8 jobs)
    jobs_data: list[dict[str, Any]] = []
    initial_locked_assignments: list[dict[str, Any]] = []

    categories = [c.value for c in JobCategory]
    priorities = [
        JobPriority.CRITICAL.value,
        JobPriority.HIGH.value,
        JobPriority.MEDIUM.value,
        JobPriority.LOW.value,
    ]

    # 1..4: COMPLETED jobs bound to tech-01 (idx 0), tech-04 (idx 3), tech-07 (idx 6), tech-11 (idx 10)
    completed_active_tech_indices = [0, 3, 6, 10]
    for i, t_idx in enumerate(completed_active_tech_indices, start=1):
        tech = technicians_data[t_idx]
        zone = tech["service_zones"][0]
        z_meta = BENGALURU_ZONES[zone]
        jid = _det_uuid(f"job-{i:03d}")
        w_start = _ist_dt(8, 0)
        w_end = _ist_dt(10, 30)
        p_start = _ist_dt(8, 15)
        p_end = _ist_dt(9, 15)
        jobs_data.append(
            {
                "id": jid,
                "customer_name": f"Synthetic Grid Facility #{i:03d} ({z_meta['locality_prefix']})",
                "customer_contact": f"+91-80-2200{i:04d}",
                "job_type": JobCategory.CIRCUIT_BREAKER_REPAIR.value,
                "description": f"[COMPLETED] Morning feeder circuit breaker replacement #{i}",
                "required_skills": [ElectricalSkill.CIRCUIT_BREAKER_REPAIR.value],
                "priority": JobPriority.HIGH.value,
                "status": JobStatus.COMPLETED.value,
                "latitude": round(z_meta["center_lat"] + 0.004, 6),
                "longitude": round(z_meta["center_lon"] + 0.004, 6),
                "service_zone": zone,
                "estimated_duration_minutes": 60,
                "appointment_window_start": w_start,
                "appointment_window_end": w_end,
                "sla_deadline": _ist_dt(11, 0),
                "assigned_technician_id": tech["id"],
                "actual_start_time": p_start,
                "actual_completion_time": p_end,
            }
        )
        initial_locked_assignments.append(
            {
                "id": _det_uuid(f"init-assign-{i:03d}"),
                "job_id": jid,
                "technician_id": tech["id"],
                "planned_start_time": p_start,
                "planned_end_time": p_end,
                "estimated_travel_minutes": 12,
                "assignment_status": "COMPLETED",
                "assignment_reason": "Completed morning dispatch",
            }
        )

    # 5..8: IN_PROGRESS jobs
    for offset, t_idx in enumerate(completed_active_tech_indices, start=5):
        tech = technicians_data[t_idx]
        zone = tech["service_zones"][0]
        z_meta = BENGALURU_ZONES[zone]
        jid = _det_uuid(f"job-{offset:03d}")
        w_start = _ist_dt(9, 30)
        w_end = _ist_dt(12, 30)
        p_start = _ist_dt(9, 45)
        p_end = _ist_dt(11, 0)
        jobs_data.append(
            {
                "id": jid,
                "customer_name": f"Synthetic Commercial Tower #{offset:03d} ({z_meta['locality_prefix']})",
                "customer_contact": f"+91-80-2200{offset:04d}",
                "job_type": JobCategory.FAULT_DIAGNOSIS.value,
                "description": f"[IN_PROGRESS] Active fault diagnosis on distribution riser #{offset}",
                "required_skills": [ElectricalSkill.ELECTRICAL_FAULT_DIAGNOSIS.value],
                "priority": JobPriority.CRITICAL.value,
                "status": JobStatus.IN_PROGRESS.value,
                "latitude": round(z_meta["center_lat"] - 0.005, 6),
                "longitude": round(z_meta["center_lon"] + 0.003, 6),
                "service_zone": zone,
                "estimated_duration_minutes": 75,
                "appointment_window_start": w_start,
                "appointment_window_end": w_end,
                "sla_deadline": _ist_dt(12, 30),
                "assigned_technician_id": tech["id"],
                "actual_start_time": p_start,
                "actual_completion_time": None,
            }
        )
        initial_locked_assignments.append(
            {
                "id": _det_uuid(f"init-assign-{offset:03d}"),
                "job_id": jid,
                "technician_id": tech["id"],
                "planned_start_time": p_start,
                "planned_end_time": p_end,
                "estimated_travel_minutes": 15,
                "assignment_status": "IN_PROGRESS",
                "assignment_reason": "Currently in-progress dispatch (protected from recovery changes)",
            }
        )

    # 9..80: Standard varied electrical service jobs (72 jobs)
    durations = [30, 45, 60, 75, 90]
    window_slots = [
        (8, 0, 12, 0),
        (9, 0, 13, 0),
        (10, 0, 15, 0),
        (11, 0, 16, 0),
        (13, 30, 18, 0),
        (14, 0, 19, 30),
        (15, 0, 20, 30),
    ]

    for j_num in range(9, 81):
        jid = _det_uuid(f"job-{j_num:03d}")
        zone = zone_keys[(j_num - 9) % len(zone_keys)]
        z_meta = BENGALURU_ZONES[zone]
        cat = categories[(j_num - 9) % len(categories)]
        req_skills = CATEGORY_TO_REQUIRED_SKILLS[cat]
        prio = priorities[(j_num * 3) % len(priorities)]
        dur = durations[(j_num * 5) % len(durations)]
        slot = window_slots[(j_num - 9) % len(window_slots)]

        w_start = _ist_dt(slot[0], slot[1])
        w_end = _ist_dt(slot[2], slot[3])
        sla_pad_hours = 1 if prio in (JobPriority.CRITICAL.value, JobPriority.HIGH.value) else 2
        sla_dt = w_end + timedelta(hours=sla_pad_hours)

        jobs_data.append(
            {
                "id": jid,
                "customer_name": f"Synthetic Consumer Unit #{j_num:03d} ({z_meta['locality_prefix']})",
                "customer_contact": f"+91-80-2200{j_num:04d}",
                "job_type": cat,
                "description": f"Scheduled {cat.lower()} service request in {zone}",
                "required_skills": req_skills,
                "priority": prio,
                "status": JobStatus.PENDING.value,
                "latitude": round(z_meta["center_lat"] + rng.uniform(-0.018, 0.018), 6),
                "longitude": round(z_meta["center_lon"] + rng.uniform(-0.018, 0.018), 6),
                "service_zone": zone,
                "estimated_duration_minutes": dur,
                "appointment_window_start": w_start,
                "appointment_window_end": w_end,
                "sla_deadline": sla_dt,
                "assigned_technician_id": None,
                "actual_start_time": None,
                "actual_completion_time": None,
            }
        )

    # 81..92: High-contention conflicting time-window cluster (12 jobs with identical tight 10:00-11:15 window)
    for j_num in range(81, 93):
        jid = _det_uuid(f"job-{j_num:03d}")
        zone = zone_keys[(j_num - 81) % len(zone_keys)]
        z_meta = BENGALURU_ZONES[zone]
        jobs_data.append(
            {
                "id": jid,
                "customer_name": f"Peak-Hour Enterprise Client #{j_num:03d}",
                "customer_contact": f"+91-80-2200{j_num:04d}",
                "job_type": JobCategory.DISTRIBUTION_BOARD_MAINTENANCE.value,
                "description": (
                    "[CONFLICTING WINDOW SCENARIO] Simultaneous peak-hour distribution board "
                    "maintenance requiring tight 10:00-11:15 slot"
                ),
                "required_skills": [
                    ElectricalSkill.DISTRIBUTION_BOARD_MAINTENANCE.value,
                    ElectricalSkill.CIRCUIT_BREAKER_REPAIR.value,
                ],
                "priority": JobPriority.HIGH.value,
                "status": JobStatus.PENDING.value,
                "latitude": round(z_meta["center_lat"] + rng.uniform(-0.01, 0.01), 6),
                "longitude": round(z_meta["center_lon"] + rng.uniform(-0.01, 0.01), 6),
                "service_zone": zone,
                "estimated_duration_minutes": 60,
                "appointment_window_start": _ist_dt(10, 0),
                "appointment_window_end": _ist_dt(11, 15),
                "sla_deadline": _ist_dt(11, 30),
                "assigned_technician_id": None,
                "actual_start_time": None,
                "actual_completion_time": None,
            }
        )

    # 93..100: Deliberately infeasible jobs (8 jobs)
    # 93..96: Require all 8 electrical skills simultaneously in zones where active techs have at most 4 skills
    for j_num in range(93, 97):
        jid = _det_uuid(f"job-{j_num:03d}")
        zone = zone_keys[(j_num - 93) % 4]
        z_meta = BENGALURU_ZONES[zone]
        jobs_data.append(
            {
                "id": jid,
                "customer_name": f"Infeasible Multi-Specialty Substation #{j_num:03d}",
                "customer_contact": f"+91-80-2200{j_num:04d}",
                "job_type": JobCategory.ELECTRICAL_INSTALLATION.value,
                "description": (
                    "[DELIBERATELY INFEASIBLE - SKILL_MISMATCH] Requires full 8-skill master "
                    "certification not held by any single active technician in zone"
                ),
                "required_skills": all_skills,
                "priority": JobPriority.MEDIUM.value,
                "status": JobStatus.UNASSIGNED.value,
                "latitude": round(z_meta["center_lat"] + 0.008, 6),
                "longitude": round(z_meta["center_lon"] - 0.008, 6),
                "service_zone": zone,
                "estimated_duration_minutes": 90,
                "appointment_window_start": _ist_dt(11, 0),
                "appointment_window_end": _ist_dt(14, 0),
                "sla_deadline": _ist_dt(15, 0),
                "assigned_technician_id": None,
                "actual_start_time": None,
                "actual_completion_time": None,
            }
        )

    # 97..100: Late-night appointment windows (22:15 - 23:45) when all zone electricians are OFF_DUTY
    for j_num in range(97, 101):
        jid = _det_uuid(f"job-{j_num:03d}")
        zone = zone_keys[(j_num - 97) % len(zone_keys)]
        z_meta = BENGALURU_ZONES[zone]
        jobs_data.append(
            {
                "id": jid,
                "customer_name": f"Off-Hours Night Facility #{j_num:03d}",
                "customer_contact": f"+91-80-2200{j_num:04d}",
                "job_type": JobCategory.WIRING_REPAIR.value,
                "description": (
                    "[DELIBERATELY INFEASIBLE - OUTSIDE_SHIFT_HOURS] Requested window "
                    "22:15-23:45 when all zone technicians are OFF_DUTY"
                ),
                "required_skills": [ElectricalSkill.RESIDENTIAL_WIRING.value],
                "priority": JobPriority.LOW.value,
                "status": JobStatus.UNASSIGNED.value,
                "latitude": round(z_meta["center_lat"] - 0.007, 6),
                "longitude": round(z_meta["center_lon"] + 0.007, 6),
                "service_zone": zone,
                "estimated_duration_minutes": 60,
                "appointment_window_start": _ist_dt(22, 15),
                "appointment_window_end": _ist_dt(23, 45),
                "sla_deadline": _ist_dt(23, 55),
                "assigned_technician_id": None,
                "actual_start_time": None,
                "actual_completion_time": None,
            }
        )

    # Generate 30 deterministic external Customer (Client) records (INDIVIDUAL & BUSINESS)
    # and link the 100 jobs to these customers.
    postal_codes = {
        "BLR-NORTH-HEBBAL": "560024",
        "BLR-SOUTH-JAYANAGAR": "560041",
        "BLR-EAST-WHITEFIELD": "560066",
        "BLR-WEST-RAJAJINAGAR": "560010",
        "BLR-CENTRAL-MG-ROAD": "560001",
        "BLR-SE-KORAMANGALA": "560034",
    }
    customers_data: list[dict[str, Any]] = []
    for c_idx in range(1, 31):
        cid = _det_uuid(f"customer-{c_idx:03d}")
        zone = zone_keys[(c_idx - 1) % len(zone_keys)]
        z_meta = BENGALURU_ZONES[zone]
        is_business = c_idx % 2 == 0
        c_type = CustomerType.BUSINESS.value if is_business else CustomerType.INDIVIDUAL.value
        full_name = (
            f"Vikram Nair (Facility Manager #{c_idx:02d})"
            if is_business
            else f"Ananya Sharma #{c_idx:02d}"
        )
        company_name = (
            f"{z_meta['locality_prefix']} Enterprises Pvt Ltd #{c_idx:02d}"
            if is_business
            else None
        )
        # Include both customers with email and customers without email (nullable email requirement)
        email = (
            None
            if c_idx % 5 == 0
            else f"client{c_idx:03d}@dispatchgrid-clients.in"
        )
        alt_phone = f"+91-80-4100{c_idx:04d}" if is_business else None

        customers_data.append(
            {
                "id": cid,
                "customer_code": f"CUST-{c_idx:04d}",
                "full_name": full_name,
                "email": email,
                "phone_number": f"+91-99001{c_idx:05d}",
                "alternate_phone_number": alt_phone,
                "customer_type": c_type,
                "company_name": company_name,
                "service_address": f"Plot #{c_idx * 4}, {z_meta['locality_prefix']}, Bengaluru",
                "city": "Bengaluru",
                "state": "Karnataka",
                "postal_code": postal_codes[zone],
                "latitude": round(z_meta["center_lat"] + ((c_idx % 5) - 2) * 0.002, 6),
                "longitude": round(z_meta["center_lon"] + ((c_idx % 5) - 2) * 0.002, 6),
                "is_active": True,
            }
        )

    for j_idx, job_item in enumerate(jobs_data):
        linked_customer = customers_data[j_idx % len(customers_data)]
        job_item["customer_id"] = linked_customer["id"]

    return {
        "customers": customers_data,
        "technicians": technicians_data,
        "jobs": jobs_data,
        "initial_locked_assignments": initial_locked_assignments,
        "initial_schedule_version_id": _det_uuid("schedule-version-001"),
        "initial_scheduling_run_id": _det_uuid("scheduling-run-001"),
    }
