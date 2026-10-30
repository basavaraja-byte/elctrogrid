"""Service helper for recording immutable audit events inside active database transactions."""

from typing import Any
import uuid

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.utils.validators import serialize_for_audit


class AuditService:
    """Transactional audit log recorder."""

    @staticmethod
    def log_event(
        db: Session,
        *,
        entity_type: str,
        entity_id: uuid.UUID,
        action: str,
        reason: str = "",
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
        schedule_version_id: uuid.UUID | None = None,
    ) -> AuditLog:
        """Create and stage an AuditLog record in the caller's database session."""
        entry = AuditLog(
            schedule_version_id=schedule_version_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_value=serialize_for_audit(old_value) if old_value is not None else None,
            new_value=serialize_for_audit(new_value) if new_value is not None else None,
            reason=reason,
        )
        db.add(entry)
        return entry

