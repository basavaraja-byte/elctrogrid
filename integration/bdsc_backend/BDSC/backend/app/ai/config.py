"""DispatchGrid AI Layer Configuration."""

from pathlib import Path
from pydantic import BaseModel, Field

# Base directories
AI_ROOT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT_DIR = AI_ROOT_DIR.parent.parent
DATA_DIR = BACKEND_ROOT_DIR / "data"
ARTIFACTS_DIR = AI_ROOT_DIR / "artifacts"
MODELS_DIR = ARTIFACTS_DIR / "models"
METRICS_DIR = ARTIFACTS_DIR / "metrics"

# Ensure runtime directories exist
MODELS_DIR.mkdir(parents=True, exist_ok=True)
METRICS_DIR.mkdir(parents=True, exist_ok=True)


class AIModelConfig(BaseModel):
    """Configuration for AI models and fallback thresholds."""

    # Default fallback durations in minutes by job type when model is uncertain or features missing
    default_duration_by_job_type: dict[str, int] = Field(
        default={
            "residential_wiring": 120,
            "commercial_wiring": 150,
            "safety_inspection": 45,
            "ev_charger_installation": 120,
            "fault_diagnosis": 60,
            "distribution_panel_repair": 120,
            "electrical_installation": 90,
            "circuit_breaker_repair": 60,
            "switch_replacement": 45,
            "default": 90,
        }
    )

    # Uncertainty bounds multiplier (e.g. 1.28 for ~80% or 1.645 for ~90% prediction interval)
    prediction_interval_z_score: float = 1.645

    # SLA Delay risk probability thresholds
    sla_risk_low_threshold: float = 0.30
    sla_risk_high_threshold: float = 0.70

    # Disruption risk probability thresholds
    disruption_risk_low_threshold: float = 0.25
    disruption_risk_high_threshold: float = 0.65

    # Random seed for reproducible training
    random_seed: int = 42

    # Model file names
    duration_model_filename: str = "duration_model.joblib"
    delay_model_filename: str = "delay_model.joblib"
    demand_model_filename: str = "demand_model.joblib"
    disruption_model_filename: str = "disruption_model.joblib"


ai_config = AIModelConfig()

