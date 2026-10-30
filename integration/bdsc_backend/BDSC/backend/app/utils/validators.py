"""Domain validators, coordinate bounds, shift policy checks, state machine, and Haversine travel math."""

from datetime import datetime, time, timedelta, timezone
import math
import re
from typing import Any
import uuid

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.models.enums import JobStatus

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
PHONE_REGEX = re.compile(r"^\+?[0-9()\-\s.]{7,25}$")


# Allowed job status transitions (Mandatory Addition #5: COMPLETED and CANCELLED are terminal;
# IN_PROGRESS cannot be arbitrarily reverted to UNASSIGNED/PENDING outside controlled cancellation)
ALLOWED_JOB_STATUS_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.PENDING: {
        JobStatus.ASSIGNED,
        JobStatus.UNASSIGNED,
        JobStatus.CANCELLED,
    },
    JobStatus.UNASSIGNED: {
        JobStatus.ASSIGNED,
        JobStatus.PENDING,
        JobStatus.CANCELLED,
    },
    JobStatus.ASSIGNED: {
        JobStatus.IN_PROGRESS,
        JobStatus.UNASSIGNED,
        JobStatus.PENDING,
        JobStatus.CANCELLED,
    },
    JobStatus.IN_PROGRESS: {
        JobStatus.COMPLETED,
        JobStatus.CANCELLED,
    },
    JobStatus.COMPLETED: set(),
    JobStatus.CANCELLED: set(),
}


def ensure_timezone_aware(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware and normalized to UTC."""
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_local_service_time(dt: datetime) -> datetime:
    """Convert any datetime to the configured local service zone timezone (default IST UTC+05:30)."""
    aware_dt = ensure_timezone_aware(dt)
    local_tz = timezone(timedelta(minutes=settings.local_timezone_offset_minutes))
    return aware_dt.astimezone(local_tz)


def validate_coordinates(latitude: float, longitude: float) -> None:
    """Validate latitude [-90, 90] and longitude [-180, 180] ranges."""
    if not (-90.0 <= latitude <= 90.0):
        raise ValidationException(
            code="VALIDATION_ERROR",
            message=f"Invalid latitude {latitude}. Must be between -90.0 and 90.0.",
            status_code=422,
            details=[{"field": "latitude", "issue": "Must be between -90.0 and 90.0"}],
        )
    if not (-180.0 <= longitude <= 180.0):
        raise ValidationException(
            code="VALIDATION_ERROR",
            message=f"Invalid longitude {longitude}. Must be between -180.0 and 180.0.",
            status_code=422,
            details=[{"field": "longitude", "issue": "Must be between -180.0 and 180.0"}],
        )


def compute_shift_duration_minutes(
    shift_start: time,
    shift_end: time,
    allow_overnight: bool | None = None,
) -> int:
    """Validate shift_start and shift_end and return total shift duration in minutes."""
    overnight_allowed = (
        settings.allow_overnight_shifts if allow_overnight is None else allow_overnight
    )
    start_minutes = shift_start.hour * 60 + shift_start.minute
    end_minutes = shift_end.hour * 60 + shift_end.minute

    if start_minutes == end_minutes:
        raise ValidationException(
            code="SHIFT_POLICY_VIOLATION",
            message="Shift end time cannot be identical to shift start time (0-minute shift).",
            status_code=422,
            details=[{"field": "shift_end", "issue": "Shift duration must be greater than 0"}],
        )

    if end_minutes > start_minutes:
        duration = end_minutes - start_minutes
        if duration > 16 * 60:
            raise ValidationException(
                code="SHIFT_POLICY_VIOLATION",
                message="Shift duration cannot exceed 16 hours.",
                status_code=422,
                details=[{"field": "shift_end", "issue": "Shift exceeds 16-hour maximum"}],
            )
        return duration

    # end_minutes < start_minutes -> overnight shift
    if not overnight_allowed:
        raise ValidationException(
            code="SHIFT_POLICY_VIOLATION",
            message="Shift end must be after shift start (overnight shifts are disabled by policy).",
            status_code=422,
            details=[
                {
                    "field": "shift_end",
                    "issue": "shift_end must be after shift_start when ALLOW_OVERNIGHT_SHIFTS is false",
                }
            ],
        )

    duration = (24 * 60 - start_minutes) + end_minutes
    if not (4 * 60 <= duration <= 16 * 60):
        raise ValidationException(
            code="SHIFT_POLICY_VIOLATION",
            message="Overnight shift duration must be between 4 and 16 hours.",
            status_code=422,
            details=[
                {
                    "field": "shift_end",
                    "issue": f"Overnight duration {duration}m outside [240m, 960m] bounds",
                }
            ],
        )
    return duration


def is_interval_within_shift(
    start_dt: datetime,
    end_dt: datetime,
    shift_start: time,
    shift_end: time,
    allow_overnight: bool | None = None,
) -> bool:
    """Check whether [start_dt, end_dt) in local service time falls completely inside [shift_start, shift_end]."""
    overnight_allowed = (
        settings.allow_overnight_shifts if allow_overnight is None else allow_overnight
    )
    local_start = to_local_service_time(start_dt)
    local_end = to_local_service_time(end_dt)

    if local_end <= local_start:
        return False

    total_job_minutes = (local_end - local_start).total_seconds() / 60.0
    start_mins = local_start.hour * 60 + local_start.minute
    end_mins = local_end.hour * 60 + local_end.minute
    shift_start_mins = shift_start.hour * 60 + shift_start.minute
    shift_end_mins = shift_end.hour * 60 + shift_end.minute

    if shift_end_mins > shift_start_mins:
        # Standard same-day shift
        if local_start.date() != local_end.date():
            return False
        return start_mins >= shift_start_mins and end_mins <= shift_end_mins

    if not overnight_allowed:
        return False

    # Overnight shift spanning midnight: e.g. 22:00 (1320) to 06:00 (360)
    shift_len = (24 * 60 - shift_start_mins) + shift_end_mins
    if total_job_minutes > shift_len:
        return False

    if start_mins >= shift_start_mins:
        offset_start = start_mins - shift_start_mins
    elif start_mins <= shift_end_mins:
        offset_start = (24 * 60 - shift_start_mins) + start_mins
    else:
        return False

    offset_end = offset_start + total_job_minutes
    return offset_end <= shift_len


def validate_job_status_transition(current_status: str, target_status: str) -> None:
    """Validate that transitioning from current_status to target_status is permitted."""
    try:
        curr_enum = JobStatus(current_status)
        target_enum = JobStatus(target_status)
    except ValueError as exc:
        raise ValidationException(
            code="INVALID_STATE_TRANSITION",
            message=f"Unknown job status in transition: {current_status} -> {target_status}",
            status_code=400,
        ) from exc

    if curr_enum == target_enum:
        return

    allowed = ALLOWED_JOB_STATUS_TRANSITIONS.get(curr_enum, set())
    if target_enum not in allowed:
        raise ValidationException(
            code="INVALID_STATE_TRANSITION",
            message=(
                f"Invalid job status transition from '{curr_enum.value}' to '{target_enum.value}'. "
                f"Allowed targets: {[s.value for s in sorted(allowed, key=lambda x: x.value)]}"
            ),
            status_code=400,
            details=[
                {
                    "current_status": curr_enum.value,
                    "requested_status": target_enum.value,
                    "allowed_transitions": [s.value for s in sorted(allowed, key=lambda x: x.value)],
                }
            ],
        )


def estimate_travel_minutes(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    avg_speed_kmh: float = 24.0,
) -> int:
    """Compute realistic urban travel time in minutes using Haversine distance and urban road factor."""
    if abs(lat1 - lat2) < 1e-6 and abs(lon1 - lon2) < 1e-6:
        return 0

    earth_radius_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    straight_distance_km = earth_radius_km * c
    # Urban road tortuosity factor 1.35x at 24 km/h average city speed
    road_distance_km = straight_distance_km * 1.35
    minutes = math.ceil((road_distance_km / avg_speed_kmh) * 60.0)
    return max(5, minutes)


def parse_iso_datetime(value: str | datetime) -> datetime:
    """Parse an ISO8601 string or datetime into a timezone-aware datetime."""
    if isinstance(value, datetime):
        return ensure_timezone_aware(value)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return ensure_timezone_aware(parsed)


def intervals_overlap(
    start_a: datetime,
    end_a: datetime,
    start_b: datetime,
    end_b: datetime,
) -> bool:
    """Return True if half-open intervals [start_a, end_a) and [start_b, end_b) overlap."""
    sa = ensure_timezone_aware(start_a)
    ea = ensure_timezone_aware(end_a)
    sb = ensure_timezone_aware(start_b)
    eb = ensure_timezone_aware(end_b)
    return sa < eb and sb < ea


def serialize_for_audit(obj: Any) -> Any:
    """Convert UUIDs, datetimes, and enums inside dicts/lists into JSON-serializable primitives."""
    if isinstance(obj, dict):
        return {str(k): serialize_for_audit(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_for_audit(item) for item in obj]
    if isinstance(obj, (datetime, time)):
        return obj.isoformat()
    if hasattr(obj, "hex") and hasattr(obj, "int"):  # UUID
        return str(obj)
    return obj


def validate_email_format(email: str | None) -> str | None:
    """Validate optional email address format; returns None if empty/None."""
    if email is None:
        return None
    cleaned = email.strip()
    if not cleaned:
        return None
    if not EMAIL_REGEX.match(cleaned):
        raise ValueError(f"Invalid email format: '{cleaned}'.")
    return cleaned.lower()


def validate_phone_format(phone: str | None, *, required: bool = False) -> str | None:
    """Validate phone number format (supports Indian +91 and international/local formats)."""
    if phone is None or not phone.strip():
        if required:
            raise ValueError("Phone number is required and cannot be empty.")
        return None
    cleaned = phone.strip()
    digits_only = re.sub(r"\D", "", cleaned)
    if not PHONE_REGEX.match(cleaned) or not (7 <= len(digits_only) <= 15):
        raise ValueError(
            f"Invalid phone number format: '{cleaned}'. Must contain 7 to 15 digits."
        )
    return cleaned


def generate_customer_code(prefix: str = "CUST") -> str:
    """Generate a unique canonical customer code (e.g. CUST-A1B2C3D4)."""
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

