"""Pydantic schemas for DispatchGrid AI prediction, risk, forecasting, and evaluation."""

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


# ============================================================================
# 1. JOB DURATION PREDICTION
# ============================================================================

class JobDurationPredictionRequest(BaseModel):
    """Input payload to predict expected service duration before assignment."""

    job_type: str = Field(..., description="Type of electrical job (e.g. residential_wiring, fault_diagnosis)")
    priority: str = Field(default="Normal", description="Job priority (Low, Normal, High, Critical)")
    required_skills: list[str] | str = Field(default_factory=list, description="List or pipe-separated skills required")
    service_zone: str = Field(default="Central", description="Service zone (Central, North, South, East, West)")
    window_start_min: int | None = Field(default=None, description="Appointment window start (minutes from midnight)")
    window_end_min: int | None = Field(default=None, description="Appointment window end (minutes from midnight)")
    sla_deadline_min: int | None = Field(default=None, description="SLA deadline (minutes from midnight)")
    estimated_duration_min: int | None = Field(default=None, description="Customer-estimated duration if specified")
    customer_type: str = Field(default="individual", description="individual or commercial")


class JobDurationPredictionResponse(BaseModel):
    """Output prediction for job duration with confidence intervals."""

    predicted_duration_min: float = Field(..., description="Point estimate of duration in minutes")
    lower_bound_min: float = Field(..., description="Estimated 90% lower bound in minutes")
    upper_bound_min: float = Field(..., description="Estimated 90% upper bound in minutes")
    confidence_score: float = Field(..., description="Empirical confidence score (0.0 to 1.0)")
    model_name: str = Field(..., description="Name of the regression model")
    model_version: str = Field(..., description="Model release version")
    prediction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    fallback_used: bool = Field(default=False, description="True if configured default fallback was returned")
    data_source: str = Field(default="SYNTHETIC_AUGMENTED", description="Provenance of underlying training data")


# ============================================================================
# 2. SLA DELAY RISK PREDICTION
# ============================================================================

class SLADelayRiskRequest(BaseModel):
    """Input payload to predict whether a job is at risk of missing its SLA deadline."""

    job_id: str | None = Field(default=None, description="Job identifier")
    job_type: str = Field(default="fault_diagnosis", description="Job category / trade type")
    priority: str = Field(default="Normal", description="Low, Normal, High, Critical")
    predicted_duration_min: float = Field(..., description="Predicted or estimated duration in minutes")
    appointment_window_start_min: int = Field(default=480, description="Window start time in minutes")
    appointment_window_end_min: int = Field(default=600, description="Window end time in minutes")
    sla_deadline_min: int = Field(default=660, description="SLA deadline time in minutes")
    estimated_travel_time_min: float = Field(default=20.0, description="Estimated technician travel time in minutes")
    service_zone: str = Field(default="Central", description="Locality or service zone")


class SLADelayRiskResponse(BaseModel):
    """Output risk prediction for SLA delay with explainability factors."""

    job_id: str | None = Field(default=None)
    delay_probability: float = Field(..., description="Probability of missing deadline (0.0 to 1.0)")
    risk_category: Literal["LOW", "MEDIUM", "HIGH"] = Field(..., description="Categorical risk tier")
    contributing_factors: list[str] = Field(default_factory=list, description="Key factors driving delay risk")
    suggested_action: str = Field(..., description="Recommended operational action for supervisor/dispatcher")
    model_name: str = Field(...)
    model_version: str = Field(...)
    prediction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    fallback_used: bool = Field(default=False)
    data_source: str = Field(default="SYNTHETIC_AUGMENTED")


# ============================================================================
# 3. DEMAND FORECASTING
# ============================================================================

class DemandForecastRequest(BaseModel):
    """Input parameters for electrical service demand forecasting."""

    service_zone: str | None = Field(default=None, description="Optional specific zone, or None for all zones")
    target_date: str | None = Field(default=None, description="Target forecast date (YYYY-MM-DD)")
    day_of_week: int | None = Field(default=None, ge=0, le=6, description="0=Monday, 6=Sunday")


class ZoneDemandForecast(BaseModel):
    """Zone-specific demand forecast output."""

    zone: str
    expected_jobs: float
    lower_bound: float
    upper_bound: float
    demand_level: Literal["LOW", "NORMAL", "HIGH", "PEAK"]


class DemandForecastResponse(BaseModel):
    """Output demand forecast for electrical service management."""

    forecast_period: str
    total_expected_jobs: float
    zone_forecasts: list[ZoneDemandForecast]
    peak_zone: str
    model_name: str
    model_version: str
    prediction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    data_source: str = Field(default="SYNTHETIC_AUGMENTED")


# ============================================================================
# 4. DISRUPTION RISK PREDICTION
# ============================================================================

class DisruptionRiskRequest(BaseModel):
    """Input payload to evaluate operational disruption risk for an assignment."""

    technician_id: str = Field(..., description="Technician ID")
    job_id: str | None = Field(default=None, description="Job ID")
    job_priority: str = Field(default="Normal")
    technician_workload_hours: float = Field(default=6.0, description="Scheduled hours on the day")
    tight_buffer_count: int = Field(default=0, description="Number of consecutive assignments with buffer < 15 min")
    service_zone: str = Field(default="Central")
    estimated_duration_min: float = Field(default=90.0)


class DisruptionRiskResponse(BaseModel):
    """Output disruption risk scoring with preventive recommendations."""

    disruption_probability: float = Field(..., description="Probability of schedule disruption (0.0 to 1.0)")
    risk_category: Literal["LOW", "MEDIUM", "HIGH"] = Field(...)
    affected_technician_id: str
    affected_job_id: str | None = None
    contributing_factors: list[str] = Field(default_factory=list)
    suggested_preventive_action: str = Field(...)
    model_name: str
    model_version: str
    prediction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    data_source: str = Field(default="SYNTHETIC_AUGMENTED")


# ============================================================================
# 5. MODEL STATUS & SYSTEM HEALTH
# ============================================================================

class ModelStatusDetail(BaseModel):
    """Health and performance metadata for a single ML model."""

    model_name: str
    is_trained: bool
    version: str
    algorithm: str
    trained_at: datetime | None = None
    training_samples: int = 0
    test_samples: int = 0
    metrics: dict[str, Any] = Field(default_factory=dict)
    data_source: str = "SYNTHETIC_AUGMENTED"


class AIHealthResponse(BaseModel):
    """System health response for the entire DispatchGrid AI layer."""

    status: Literal["healthy", "degraded", "untrained"]
    all_models_ready: bool
    models: dict[str, ModelStatusDetail]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

