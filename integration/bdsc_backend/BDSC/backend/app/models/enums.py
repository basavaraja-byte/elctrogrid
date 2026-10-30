"""Canonical enumerations shared across models, schemas, and services."""

from enum import StrEnum


class AvailabilityStatus(StrEnum):
    """Technician operational availability states (Mandatory Addition #2)."""

    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    ON_BREAK = "ON_BREAK"
    UNAVAILABLE = "UNAVAILABLE"
    OFF_DUTY = "OFF_DUTY"


class CustomerType(StrEnum):
    """Customer classification (external individual or business requesting service)."""

    INDIVIDUAL = "INDIVIDUAL"
    BUSINESS = "BUSINESS"


class JobPriority(StrEnum):
    """Electrical service job priority levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class JobStatus(StrEnum):
    """Lifecycle states of an electrical service job."""

    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    UNASSIGNED = "UNASSIGNED"


class AssignmentStatus(StrEnum):
    """Lifecycle states of a planned technician-to-job assignment."""

    PLANNED = "PLANNED"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REASSIGNED = "REASSIGNED"


class ScheduleVersionStatus(StrEnum):
    """Lifecycle states of a schedule version (Mandatory Addition #3 & #4)."""

    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"


class SchedulingRunType(StrEnum):
    """Category of scheduling execution run."""

    INITIAL = "INITIAL"
    OPTIMIZATION = "OPTIMIZATION"
    RECOVERY = "RECOVERY"


class SchedulingStrategy(StrEnum):
    """Supported scheduling strategies."""

    BALANCED = "BALANCED"
    MINIMIZE_TRAVEL = "MINIMIZE_TRAVEL"
    SLA_FIRST = "SLA_FIRST"
    STABILITY_FIRST = "STABILITY_FIRST"


class ExecutionStatus(StrEnum):
    """Execution status of a scheduling run."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ElectricalSkill(StrEnum):
    """Canonical electrical skills supported across the workforce."""

    RESIDENTIAL_WIRING = "Residential wiring"
    INDUSTRIAL_WIRING = "Industrial wiring"
    CIRCUIT_BREAKER_REPAIR = "Circuit breaker repair"
    SWITCH_AND_SOCKET_REPLACEMENT = "Switch and socket replacement"
    ELECTRICAL_FAULT_DIAGNOSIS = "Electrical fault diagnosis"
    DISTRIBUTION_BOARD_MAINTENANCE = "Distribution board maintenance"
    EARTHING_AND_GROUNDING = "Earthing and grounding"
    ELECTRICAL_INSTALLATION = "Electrical installation"


class JobCategory(StrEnum):
    """Canonical electrical job categories."""

    FAULT_DIAGNOSIS = "Fault diagnosis"
    WIRING_REPAIR = "Wiring repair"
    SWITCH_REPLACEMENT = "Switch replacement"
    CIRCUIT_BREAKER_REPAIR = "Circuit breaker repair"
    ELECTRICAL_INSTALLATION = "Electrical installation"
    DISTRIBUTION_BOARD_MAINTENANCE = "Distribution board maintenance"


class SLARiskLevel(StrEnum):
    """SLA risk classification for planned assignments."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BREACHED = "BREACHED"


class AssignmentChangeType(StrEnum):
    """Classification of assignment changes between two schedule versions."""

    UNCHANGED = "UNCHANGED"
    REASSIGNED_TECHNICIAN = "REASSIGNED_TECHNICIAN"
    TIME_SHIFTED = "TIME_SHIFTED"
    NEWLY_ASSIGNED = "NEWLY_ASSIGNED"
    NEWLY_UNASSIGNED = "NEWLY_UNASSIGNED"


CANONICAL_ELECTRICAL_SKILLS: set[str] = {skill.value for skill in ElectricalSkill}
CANONICAL_JOB_CATEGORIES: set[str] = {cat.value for cat in JobCategory}

