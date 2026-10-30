"""FastAPI routes for DispatchGrid AI prediction, risk assessment, and model evaluation."""

from __future__ import annotations

import json
from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, status

from app.ai.config import METRICS_DIR
from app.ai.schemas import (
    AIHealthResponse,
    DemandForecastRequest,
    DemandForecastResponse,
    DisruptionRiskRequest,
    DisruptionRiskResponse,
    JobDurationPredictionRequest,
    JobDurationPredictionResponse,
    SLADelayRiskRequest,
    SLADelayRiskResponse,
)
from app.ai.services import ai_service
from app.ai.training.train_all import train_all_models

router = APIRouter(prefix="/api/v1/ai", tags=["AI & Machine Learning"])


@router.post(
    "/predict-duration",
    response_model=JobDurationPredictionResponse,
    summary="Predict job service duration using trained regression model with uncertainty bounds",
)
async def predict_job_duration(payload: JobDurationPredictionRequest) -> JobDurationPredictionResponse:
    """Returns point estimate duration (min) and 90% confidence bounds based on trade complexity."""
    return ai_service.predict_duration(payload)


@router.post(
    "/predict-delay-risk",
    response_model=SLADelayRiskResponse,
    summary="Evaluate SLA deadline breach risk with explainable contributing factors",
)
async def predict_sla_delay_risk(payload: SLADelayRiskRequest) -> SLADelayRiskResponse:
    """Classifies SLA delay risk into LOW, MEDIUM, or HIGH and provides actionable guidance."""
    return ai_service.predict_delay_risk(payload)


@router.post(
    "/forecast-demand",
    response_model=DemandForecastResponse,
    summary="Forecast electrical service job demand across urban zones",
)
async def forecast_electrical_demand(
    payload: DemandForecastRequest = Body(default_factory=DemandForecastRequest),
) -> DemandForecastResponse:
    """Predicts expected ticket volume per zone for next 24h using chronological time-series model."""
    return ai_service.forecast_demand(payload)


@router.post(
    "/predict-disruption-risk",
    response_model=DisruptionRiskResponse,
    summary="Evaluate operational disruption risk for scheduled technician assignments",
)
async def predict_disruption_risk(payload: DisruptionRiskRequest) -> DisruptionRiskResponse:
    """Assesses technician workload compression and flags schedule instability."""
    return ai_service.predict_disruption_risk(payload)


@router.get(
    "/model-status",
    response_model=AIHealthResponse,
    summary="Get operational status and health metrics for all 4 trained AI models",
)
async def get_ai_model_status() -> AIHealthResponse:
    """Inspects trained pipelines, algorithms, sample sizes, and current readiness status."""
    return ai_service.get_model_status()


@router.get(
    "/evaluation",
    summary="Retrieve comprehensive training and evaluation reports for all candidate models",
)
async def get_model_evaluation_reports() -> dict:
    """Returns baseline vs candidate metrics (MAE, RMSE, R2, F1, ROC-AUC, WAPE) across all models."""
    reports = {}
    for fname in ["duration_metrics.json", "delay_metrics.json", "demand_metrics.json", "disruption_metrics.json"]:
        p = METRICS_DIR / fname
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    reports[fname.replace("_metrics.json", "")] = json.load(f)
            except Exception as exc:
                reports[fname] = {"error": str(exc)}
    return reports


@router.post(
    "/retrain",
    summary="Trigger model retraining across all 4 ML models",
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_model_retraining(background_tasks: BackgroundTasks) -> dict[str, str]:
    """Retrains all 4 models and updates the in-memory inference pipelines."""
    def _retrain_and_reload():
        train_all_models()
        ai_service._load_artifacts()

    background_tasks.add_task(_retrain_and_reload)
    return {
        "status": "accepted",
        "message": "AI model re-training pipeline started in the background. Artifacts will reload automatically upon completion.",
    }
