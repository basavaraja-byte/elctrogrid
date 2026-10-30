"""Technician management service with time-aware availability checks and audit logging."""

from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.models.assignment import Assignment
from app.models.enums import AvailabilityStatus, ScheduleVersionStatus
from app.models.schedule import ScheduleVersion
from app.models.technician import Technician
from app.schemas.technician import (
    TechnicianAvailabilityPatch,
    TechnicianCreate,
    TechnicianUpdate,
    TechnicianWindowAvailabilityResponse,
)
from app.services.audit_service import AuditService
from app.utils.validators import (
    compute_shift_duration_minutes,
    ensure_timezone_aware,
    intervals_overlap,
    is_interval_within_shift,
    parse_iso_datetime,
    validate_coordinates,
)


class TechnicianService:
    """Service layer for Electrician Technician CRUD and time-aware availability evaluation."""

    @staticmethod
    def _serialize_windows(windows: list[Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for w in windows:
            if isinstance(w, dict):
                result.append(
                    {
                        "start": parse_iso_datetime(w["start"]).isoformat(),
                        "end": parse_iso_datetime(w["end"]).isoformat(),
                        "status": str(w.get("status", AvailabilityStatus.ON_BREAK.value)),
                        "reason": str(w.get("reason", "Scheduled break")),
                    }
                )
            else:
                result.append(
                    {
                        "start": ensure_timezone_aware(w.start).isoformat(),
                        "end": ensure_timezone_aware(w.end).isoformat(),
                        "status": w.status.value,
                        "reason": w.reason,
                    }
                )
        return result

    @classmethod
    def create_technician(cls, db: Session, payload: TechnicianCreate) -> Technician:
        """Validate and create a new electrician technician."""
        validate_coordinates(payload.latitude, payload.longitude)
        compute_shift_duration_minutes(payload.shift_start, payload.shift_end)

        tech = Technician(
            name=payload.name.strip(),
            phone=payload.phone.strip() if payload.phone else None,
            skills=payload.skills,
            service_zones=payload.service_zones,
            latitude=payload.latitude,
            longitude=payload.longitude,
            shift_start=payload.shift_start,
            shift_end=payload.shift_end,
            is_active=payload.is_active,
            availability_status=payload.availability_status.value,
            unavailable_windows=cls._serialize_windows(payload.unavailable_windows),
        )
        db.add(tech)
        db.flush()

        AuditService.log_event(
            db,
            entity_type="TECHNICIAN",
            entity_id=tech.id,
            action="CREATE",
            new_value={
                "name": tech.name,
                "skills": tech.skills,
                "service_zones": tech.service_zones,
                "availability_status": tech.availability_status,
                "is_active": tech.is_active,
            },
            reason="Created electrician technician",
        )
        db.commit()
        db.refresh(tech)
        return tech

    @staticmethod
    def get_technician_by_id(db: Session, technician_id: uuid.UUID) -> Technician:
        """Retrieve a technician by UUID or raise 404 NotFoundException."""
        tech = db.get(Technician, technician_id)
        if not tech:
            raise NotFoundException("Technician", technician_id)
        return tech

    @classmethod
    def check_availability_in_window(
        cls,
        technician: Technician,
        window_start: datetime,
        window_end: datetime,
        existing_assignments: list[Assignment] | None = None,
    ) -> TechnicianWindowAvailabilityResponse:
        """Evaluate time-aware availability of a technician during [window_start, window_end)."""
        ws = ensure_timezone_aware(window_start)
        we = ensure_timezone_aware(window_end)
        if we <= ws:
            raise ValidationException(
                code="VALIDATION_ERROR",
                message="window_end must be strictly after window_start.",
                status_code=422,
            )

        if not technician.is_active:
            return TechnicianWindowAvailabilityResponse(
                technician_id=technician.id,
                technician_name=technician.name,
                window_start=ws,
                window_end=we,
                is_available=False,
                effective_status=AvailabilityStatus.UNAVAILABLE,
                blocking_reason="Technician is marked inactive (is_active=False).",
            )

        if technician.availability_status == AvailabilityStatus.UNAVAILABLE.value:
            return TechnicianWindowAvailabilityResponse(
                technician_id=technician.id,
                technician_name=technician.name,
                window_start=ws,
                window_end=we,
                is_available=False,
                effective_status=AvailabilityStatus.UNAVAILABLE,
                blocking_reason="Technician status is globally UNAVAILABLE.",
            )

        if not is_interval_within_shift(ws, we, technician.shift_start, technician.shift_end):
            return TechnicianWindowAvailabilityResponse(
                technician_id=technician.id,
                technician_name=technician.name,
                window_start=ws,
                window_end=we,
                is_available=False,
                effective_status=AvailabilityStatus.OFF_DUTY,
                blocking_reason=(
                    f"Requested window lies outside technician shift hours "
                    f"({technician.shift_start.isoformat()} - {technician.shift_end.isoformat()})."
                ),
            )

        # Check time-bounded unavailable / break windows
        for win in technician.unavailable_windows or []:
            win_start = parse_iso_datetime(win["start"])
            win_end = parse_iso_datetime(win["end"])
            if intervals_overlap(ws, we, win_start, win_end):
                win_status_str = win.get("status", AvailabilityStatus.ON_BREAK.value)
                try:
                    eff_status = AvailabilityStatus(win_status_str)
                except ValueError:
                    eff_status = AvailabilityStatus.ON_BREAK
                return TechnicianWindowAvailabilityResponse(
                    technician_id=technician.id,
                    technician_name=technician.name,
                    window_start=ws,
                    window_end=we,
                    is_available=False,
                    effective_status=eff_status,
                    blocking_reason=(
                        f"Overlaps technician {eff_status.value} window "
                        f"({win_start.isoformat()} - {win_end.isoformat()}): {win.get('reason', '')}"
                    ),
                )

        # Check existing assignments in the active/target schedule
        if existing_assignments:
            for assign in existing_assignments:
                if assign.technician_id == technician.id and intervals_overlap(
                    ws, we, assign.planned_start_time, assign.planned_end_time
                ):
                    return TechnicianWindowAvailabilityResponse(
                        technician_id=technician.id,
                        technician_name=technician.name,
                        window_start=ws,
                        window_end=we,
                        is_available=False,
                        effective_status=AvailabilityStatus.BUSY,
                        blocking_reason=(
                            f"Technician already assigned to job {assign.job_id} during "
                            f"{ensure_timezone_aware(assign.planned_start_time).isoformat()} - "
                            f"{ensure_timezone_aware(assign.planned_end_time).isoformat()}."
                        ),
                    )

        return TechnicianWindowAvailabilityResponse(
            technician_id=technician.id,
            technician_name=technician.name,
            window_start=ws,
            window_end=we,
            is_available=True,
            effective_status=AvailabilityStatus.AVAILABLE,
            blocking_reason=None,
        )

    @classmethod
    def list_technicians(
        cls,
        db: Session,
        *,
        availability_status: AvailabilityStatus | None = None,
        skill: str | None = None,
        service_zone: str | None = None,
        is_active: bool | None = None,
        available_from: datetime | None = None,
        available_until: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Technician]:
        """List technicians with optional attribute and time-window availability filters."""
        stmt = select(Technician).order_by(Technician.created_at.asc())

        if availability_status is not None:
            stmt = stmt.where(Technician.availability_status == availability_status.value)
        if is_active is not None:
            stmt = stmt.where(Technician.is_active == is_active)

        technicians = list(db.scalars(stmt).all())

        # Filter JSON list fields in Python for cross-database compatibility (PostgreSQL + SQLite)
        if skill:
            skill_lower = skill.strip().lower()
            technicians = [
                t
                for t in technicians
                if any(s.lower() == skill_lower for s in (t.skills or []))
            ]

        if service_zone:
            zone_lower = service_zone.strip().lower()
            technicians = [
                t
                for t in technicians
                if any(z.lower() == zone_lower for z in (t.service_zones or []))
            ]

        if available_from is not None and available_until is not None:
            active_version = db.scalar(
                select(ScheduleVersion).where(
                    ScheduleVersion.status == ScheduleVersionStatus.ACTIVE.value
                )
            )
            active_assignments = active_version.assignments if active_version else []
            technicians = [
                t
                for t in technicians
                if cls.check_availability_in_window(
                    t, available_from, available_until, active_assignments
                ).is_available
            ]

        return technicians[skip : skip + limit]

    @classmethod
    def update_technician(
        cls,
        db: Session,
        technician_id: uuid.UUID,
        payload: TechnicianUpdate,
    ) -> Technician:
        """Full update of a technician record."""
        tech = cls.get_technician_by_id(db, technician_id)
        validate_coordinates(payload.latitude, payload.longitude)
        compute_shift_duration_minutes(payload.shift_start, payload.shift_end)

        old_snapshot = {
            "name": tech.name,
            "skills": tech.skills,
            "service_zones": tech.service_zones,
            "shift_start": tech.shift_start.isoformat(),
            "shift_end": tech.shift_end.isoformat(),
            "is_active": tech.is_active,
            "availability_status": tech.availability_status,
            "unavailable_windows": tech.unavailable_windows,
        }

        tech.name = payload.name.strip()
        tech.phone = payload.phone.strip() if payload.phone else None
        tech.skills = payload.skills
        tech.service_zones = payload.service_zones
        tech.latitude = payload.latitude
        tech.longitude = payload.longitude
        tech.shift_start = payload.shift_start
        tech.shift_end = payload.shift_end
        tech.is_active = payload.is_active
        tech.availability_status = payload.availability_status.value
        tech.unavailable_windows = cls._serialize_windows(payload.unavailable_windows)

        new_snapshot = {
            "name": tech.name,
            "skills": tech.skills,
            "service_zones": tech.service_zones,
            "shift_start": tech.shift_start.isoformat(),
            "shift_end": tech.shift_end.isoformat(),
            "is_active": tech.is_active,
            "availability_status": tech.availability_status,
            "unavailable_windows": tech.unavailable_windows,
        }

        AuditService.log_event(
            db,
            entity_type="TECHNICIAN",
            entity_id=tech.id,
            action="UPDATE",
            old_value=old_snapshot,
            new_value=new_snapshot,
            reason="Updated technician profile",
        )
        db.commit()
        db.refresh(tech)
        return tech

    @classmethod
    def patch_availability(
        cls,
        db: Session,
        technician_id: uuid.UUID,
        payload: TechnicianAvailabilityPatch,
    ) -> Technician:
        """Update technician availability status, active flag, and optional break/unavailable window."""
        tech = cls.get_technician_by_id(db, technician_id)
        old_snapshot = {
            "availability_status": tech.availability_status,
            "is_active": tech.is_active,
            "unavailable_windows": list(tech.unavailable_windows or []),
        }

        tech.availability_status = payload.availability_status.value
        if payload.is_active is not None:
            tech.is_active = payload.is_active

        windows = list(tech.unavailable_windows or [])
        if payload.clear_unavailable_windows:
            windows = []
        if payload.unavailable_window is not None:
            windows.append(
                {
                    "start": ensure_timezone_aware(payload.unavailable_window.start).isoformat(),
                    "end": ensure_timezone_aware(payload.unavailable_window.end).isoformat(),
                    "status": payload.unavailable_window.status.value,
                    "reason": payload.unavailable_window.reason,
                }
            )
        tech.unavailable_windows = windows

        new_snapshot = {
            "availability_status": tech.availability_status,
            "is_active": tech.is_active,
            "unavailable_windows": tech.unavailable_windows,
        }

        AuditService.log_event(
            db,
            entity_type="TECHNICIAN",
            entity_id=tech.id,
            action="AVAILABILITY_CHANGE",
            old_value=old_snapshot,
            new_value=new_snapshot,
            reason=payload.reason,
        )
        db.commit()
        db.refresh(tech)
        return tech

