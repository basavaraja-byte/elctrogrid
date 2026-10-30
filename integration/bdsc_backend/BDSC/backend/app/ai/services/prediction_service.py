"""Inference and risk scoring service powered by trained DispatchGrid AI models."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.ai.config import METRICS_DIR, MODELS_DIR, ai_config
from app.ai.data_prep import engineer_delay_features, engineer_disruption_features
from app.ai.schemas import (
    AIHealthResponse,
    DemandForecastRequest,
    DemandForecastResponse,
    DisruptionRiskRequest,
    DisruptionRiskResponse,
    JobDurationPredictionRequest,
    JobDurationPredictionResponse,
    ModelStatusDetail,
    SLADelayRiskRequest,
    SLADelayRiskResponse,
    ZoneDemandForecast,
)
from app.ai.services.explanation_service import ExplanationService

logger = logging.getLogger("dispatchgrid.ai.service")


class AIPredictionService:
    """Enterprise AI Prediction & Risk Evaluation Service."""

    def __init__(self) -> None:
        self.duration_artifact: dict[str, Any] | None = None
        self.delay_artifact: dict[str, Any] | None = None
        self.demand_artifact: dict[str, Any] | None = None
        self.disruption_artifact: dict[str, Any] | None = None
        self._load_artifacts()

    def _load_artifacts(self) -> None:
        """Load trained model artifacts and metadata from disk."""
        models = [
            ("duration", ai_config.duration_model_filename),
            ("delay", ai_config.delay_model_filename),
            ("demand", ai_config.demand_model_filename),
            ("disruption", ai_config.disruption_model_filename),
        ]
        for attr, fname in models:
            path = MODELS_DIR / fname
            if path.exists():
                try:
                    payload = joblib.load(path)
                    setattr(self, f"{attr}_artifact", payload)
                    logger.info(f"Loaded {attr} model from {path}")
                except Exception as exc:
                    logger.error(f"Failed loading {attr} model: {exc}")
            else:
                logger.warning(f"Model artifact not found at {path}")

    # =========================================================================
    # 1. JOB DURATION PREDICTION
    # =========================================================================
    def predict_duration(self, request: JobDurationPredictionRequest) -> JobDurationPredictionResponse:
        """Predict expected duration of an electrical service job with uncertainty bounds."""
        job_type = request.job_type.lower().strip()
        default_fallback = ai_config.default_duration_by_job_type.get(
            job_type, ai_config.default_duration_by_job_type["default"]
        )

        if self.duration_artifact is None:
            return JobDurationPredictionResponse(
                predicted_duration_min=float(default_fallback),
                lower_bound_min=float(max(15, default_fallback - 20)),
                upper_bound_min=float(default_fallback + 30),
                confidence_score=0.50,
                model_name="ConfiguredDefaultFallback",
                model_version="0.0.0",
                fallback_used=True,
                data_source="DEFAULT_CONFIG",
            )

        try:
            pipeline = self.duration_artifact["pipeline"]
            meta = self.duration_artifact["metadata"]

            # Skill count computation
            if isinstance(request.required_skills, list):
                skill_count = len(request.required_skills)
            elif isinstance(request.required_skills, str) and request.required_skills:
                skill_count = len(request.required_skills.split("|"))
            else:
                skill_count = 1

            # Window span computation
            if request.window_start_min is not None and request.window_end_min is not None:
                window_span = max(30, request.window_end_min - request.window_start_min)
                hour_of_day = request.window_start_min // 60
            else:
                window_span = 120
                hour_of_day = 10

            est_dur = float(request.estimated_duration_min or default_fallback)

            input_df = pd.DataFrame([{
                "job_type": job_type,
                "priority": request.priority,
                "service_zone": request.service_zone,
                "customer_type": request.customer_type,
                "skill_count": skill_count,
                "window_span_min": window_span,
                "estimated_duration_min": est_dur,
                "hour_of_day": hour_of_day,
                "day_of_week": datetime.now(timezone.utc).weekday(),
            }])

            pred = float(pipeline.predict(input_df)[0])
            pred = max(15.0, min(360.0, pred))

            residual_std = float(meta.get("residual_std", 20.0))
            z = ai_config.prediction_interval_z_score
            lower = max(15.0, pred - z * residual_std)
            upper = pred + z * residual_std

            # Empirical confidence score (higher if predicted within normal distribution)
            confidence = max(0.60, min(0.95, 1.0 - (residual_std / (pred + 1.0)) * 0.5))

            return JobDurationPredictionResponse(
                predicted_duration_min=round(pred, 1),
                lower_bound_min=round(lower, 1),
                upper_bound_min=round(upper, 1),
                confidence_score=round(confidence, 2),
                model_name=meta.get("model_name", "LinearRegression"),
                model_version=meta.get("version", "1.0.0"),
                fallback_used=False,
                data_source=meta.get("data_provenance", "SYNTHETIC_AUGMENTED"),
            )
        except Exception as exc:
            logger.error(f"Error predicting duration: {exc}")
            return JobDurationPredictionResponse(
                predicted_duration_min=float(default_fallback),
                lower_bound_min=float(max(15, default_fallback - 20)),
                upper_bound_min=float(default_fallback + 30),
                confidence_score=0.50,
                model_name="FallbackOnError",
                model_version="0.0.0",
                fallback_used=True,
                data_source="DEFAULT_CONFIG",
            )

    # =========================================================================
    # 2. SLA DELAY RISK PREDICTION
    # =========================================================================
    def predict_delay_risk(self, request: SLADelayRiskRequest) -> SLADelayRiskResponse:
        """Predict probability of missing SLA deadline with explainable factors."""
        slack_min = float(request.sla_deadline_min - request.appointment_window_start_min)
        slack_min = max(1.0, slack_min)
        buffer_slack = slack_min - (request.predicted_duration_min + request.estimated_travel_time_min)

        if self.delay_artifact is None:
            # Rule-based fallback
            is_delayed = buffer_slack < 20.0
            prob = 0.85 if is_delayed else 0.15
            tier = "HIGH" if prob >= 0.70 else ("MEDIUM" if prob >= 0.30 else "LOW")
            factors, action = ExplanationService.explain_sla_delay(
                job_id=request.job_id,
                job_type=request.job_type,
                priority=request.priority,
                delay_prob=prob,
                predicted_duration=request.predicted_duration_min,
                slack_min=slack_min,
                travel_min=request.estimated_travel_time_min,
                buffer_slack=buffer_slack,
            )
            return SLADelayRiskResponse(
                job_id=request.job_id,
                delay_probability=round(prob, 2),
                risk_category=tier,
                contributing_factors=factors,
                suggested_action=action,
                model_name="RuleBasedHeuristicFallback",
                model_version="0.0.0",
                fallback_used=True,
                data_source="DEFAULT_CONFIG",
            )

        try:
            pipeline = self.delay_artifact["pipeline"]
            meta = self.delay_artifact["metadata"]

            raw_df = pd.DataFrame([{
                "job_type": request.job_type,
                "priority": request.priority,
                "service_zone": request.service_zone,
                "predicted_duration_min": request.predicted_duration_min,
                "sla_slack_min": slack_min,
                "estimated_travel_min": request.estimated_travel_time_min,
            }])
            feat_df = engineer_delay_features(raw_df)

            prob = float(pipeline.predict_proba(feat_df)[0, 1])

            if prob >= ai_config.sla_risk_high_threshold:
                tier = "HIGH"
            elif prob >= ai_config.sla_risk_low_threshold:
                tier = "MEDIUM"
            else:
                tier = "LOW"

            factors, action = ExplanationService.explain_sla_delay(
                job_id=request.job_id,
                job_type=request.job_type,
                priority=request.priority,
                delay_prob=prob,
                predicted_duration=request.predicted_duration_min,
                slack_min=slack_min,
                travel_min=request.estimated_travel_time_min,
                buffer_slack=buffer_slack,
            )

            return SLADelayRiskResponse(
                job_id=request.job_id,
                delay_probability=round(prob, 4),
                risk_category=tier,
                contributing_factors=factors,
                suggested_action=action,
                model_name=meta.get("model_name", "RandomForestClassifier"),
                model_version=meta.get("version", "1.0.0"),
                fallback_used=False,
                data_source=meta.get("data_provenance", "SYNTHETIC_AUGMENTED"),
            )
        except Exception as exc:
            logger.error(f"Error predicting delay risk: {exc}")
            prob = 0.50
            return SLADelayRiskResponse(
                job_id=request.job_id,
                delay_probability=prob,
                risk_category="MEDIUM",
                contributing_factors=[f"Prediction error occurred: {exc}. Relying on conservative safety margin."],
                suggested_action="Review assignment manually in Supervisor dashboard.",
                model_name="FallbackOnError",
                model_version="0.0.0",
                fallback_used=True,
                data_source="DEFAULT_CONFIG",
            )

    # =========================================================================
    # 3. DEMAND FORECASTING
    # =========================================================================
    def forecast_demand(self, request: DemandForecastRequest) -> DemandForecastResponse:
        """Forecast expected daily incoming jobs by zone."""
        zones = [request.service_zone] if request.service_zone else ["Central", "North", "South", "East", "West"]
        dow = request.day_of_week if request.day_of_week is not None else datetime.now(timezone.utc).weekday()
        is_weekend = 1 if dow in [5, 6] else 0

        forecasts: list[ZoneDemandForecast] = []
        meta = self.demand_artifact["metadata"] if self.demand_artifact else {}
        pipeline = self.demand_artifact["pipeline"] if self.demand_artifact else None
        zone_baselines = meta.get("zone_baseline_means", {
            "Central": 16.0, "North": 11.0, "South": 10.0, "East": 8.0, "West": 7.0
        })

        for z in zones:
            baseline = zone_baselines.get(z, 10.0)
            if pipeline is not None:
                try:
                    input_df = pd.DataFrame([{
                        "service_zone": z,
                        "day_of_week": dow,
                        "is_weekend": is_weekend,
                        "season_sin": 0.5,
                        "season_cos": 0.86,
                        "rolling_avg_7d": baseline,
                    }])
                    val = float(max(1.0, pipeline.predict(input_df)[0]))
                except Exception:
                    val = baseline
            else:
                val = baseline

            lower = max(1.0, val * 0.8)
            upper = val * 1.25

            if val >= 14.0:
                tier = "PEAK" if val >= 18.0 else "HIGH"
            elif val <= 6.0:
                tier = "LOW"
            else:
                tier = "NORMAL"

            forecasts.append(ZoneDemandForecast(
                zone=z,
                expected_jobs=round(val, 1),
                lower_bound=round(lower, 1),
                upper_bound=round(upper, 1),
                demand_level=tier,
            ))

        total = sum(f.expected_jobs for f in forecasts)
        peak_zone = max(forecasts, key=lambda f: f.expected_jobs).zone

        return DemandForecastResponse(
            forecast_period=f"Next 24h ({request.target_date or 'Today'})",
            total_expected_jobs=round(total, 1),
            zone_forecasts=forecasts,
            peak_zone=peak_zone,
            model_name=meta.get("model_name", "RidgeDemandForecaster"),
            model_version=meta.get("version", "1.0.0"),
            data_source=meta.get("data_provenance", "SYNTHETIC_AUGMENTED"),
        )

    # =========================================================================
    # 4. DISRUPTION RISK PREDICTION
    # =========================================================================
    def predict_disruption_risk(self, request: DisruptionRiskRequest) -> DisruptionRiskResponse:
        """Evaluate operational schedule disruption risk for an assignment."""
        if self.disruption_artifact is None:
            prob = 0.20
            factors, action = ExplanationService.explain_disruption_risk(
                request.technician_id, request.technician_workload_hours, request.tight_buffer_count, prob
            )
            return DisruptionRiskResponse(
                disruption_probability=prob,
                risk_category="LOW",
                affected_technician_id=request.technician_id,
                affected_job_id=request.job_id,
                contributing_factors=factors,
                suggested_preventive_action=action,
                model_name="RuleBasedFallback",
                model_version="0.0.0",
                data_source="DEFAULT_CONFIG",
            )

        try:
            pipeline = self.disruption_artifact["pipeline"]
            meta = self.disruption_artifact["metadata"]

            raw_df = pd.DataFrame([{
                "job_priority": request.job_priority,
                "service_zone": request.service_zone,
                "technician_workload_hours": request.technician_workload_hours,
                "tight_buffer_count": request.tight_buffer_count,
                "estimated_duration_min": request.estimated_duration_min,
            }])
            feat_df = engineer_disruption_features(raw_df)

            prob = float(pipeline.predict_proba(feat_df)[0, 1])

            if prob >= ai_config.disruption_risk_high_threshold:
                tier = "HIGH"
            elif prob >= ai_config.disruption_risk_low_threshold:
                tier = "MEDIUM"
            else:
                tier = "LOW"

            factors, action = ExplanationService.explain_disruption_risk(
                request.technician_id, request.technician_workload_hours, request.tight_buffer_count, prob
            )

            return DisruptionRiskResponse(
                disruption_probability=round(prob, 4),
                risk_category=tier,
                affected_technician_id=request.technician_id,
                affected_job_id=request.job_id,
                contributing_factors=factors,
                suggested_preventive_action=action,
                model_name=meta.get("model_name", "HistGradientBoostingClassifier"),
                model_version=meta.get("version", "1.0.0"),
                data_source=meta.get("data_provenance", "SYNTHETIC_AUGMENTED"),
            )
        except Exception as exc:
            logger.error(f"Error predicting disruption risk: {exc}")
            prob = 0.35
            return DisruptionRiskResponse(
                disruption_probability=prob,
                risk_category="MEDIUM",
                affected_technician_id=request.technician_id,
                affected_job_id=request.job_id,
                contributing_factors=[f"Prediction error occurred: {exc}"],
                suggested_preventive_action="Monitor technician schedule manually.",
                model_name="FallbackOnError",
                model_version="0.0.0",
                data_source="DEFAULT_CONFIG",
            )

    # =========================================================================
    # 5. MODEL STATUS & HEALTH
    # =========================================================================
    def get_model_status(self) -> AIHealthResponse:
        """Return operational health and evaluation metrics across all 4 models."""
        models: dict[str, ModelStatusDetail] = {}

        specs = [
            ("duration", self.duration_artifact, "Job Duration Regressor", "duration_metrics.json"),
            ("delay", self.delay_artifact, "SLA Delay Classifier", "delay_metrics.json"),
            ("demand", self.demand_artifact, "Demand Forecaster", "demand_metrics.json"),
            ("disruption", self.disruption_artifact, "Disruption Risk Classifier", "disruption_metrics.json"),
        ]

        trained_count = 0
        for key, artifact, default_name, metrics_fname in specs:
            metrics_file = METRICS_DIR / metrics_fname
            file_meta = {}
            if metrics_file.exists():
                try:
                    with open(metrics_file, "r", encoding="utf-8") as f:
                        file_meta = json.load(f)
                except Exception:
                    pass

            is_trained = artifact is not None or bool(file_meta)
            if is_trained:
                trained_count += 1

            meta = artifact["metadata"] if artifact else file_meta

            models[key] = ModelStatusDetail(
                model_name=meta.get("model_name", default_name),
                is_trained=is_trained,
                version=meta.get("version", "1.0.0"),
                algorithm=meta.get("model_name", "Unknown"),
                trained_at=meta.get("trained_at"),
                training_samples=meta.get("training_samples", 0),
                test_samples=meta.get("test_samples", 0),
                metrics=meta.get("metrics", {}),
                data_source=meta.get("data_provenance", "SYNTHETIC_AUGMENTED"),
            )

        status = "healthy" if trained_count == 4 else ("degraded" if trained_count > 0 else "untrained")
        return AIHealthResponse(
            status=status,
            all_models_ready=(trained_count == 4),
            models=models,
        )


# Global singleton instance
ai_service = AIPredictionService()

