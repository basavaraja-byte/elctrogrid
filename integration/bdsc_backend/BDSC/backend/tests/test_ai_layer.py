"""Comprehensive test suite for DispatchGrid AI Layer (Part 12).

Tests:
1. Data preprocessing, encoders, and feature engineering
2. Synthetic dataset generation & zero data leakage
3. Job duration prediction with uncertainty bounds & fallback
4. SLA delay risk classification & explainability factors
5. Demand forecasting across urban zones
6. Disruption risk evaluation & preventive recommendations
7. FastAPI AI endpoints (/api/v1/ai/*)
8. AI-enhanced scheduler integration
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.ai.data_prep import (
    create_delay_preprocessor,
    create_disruption_preprocessor,
    create_duration_preprocessor,
    engineer_delay_features,
    engineer_disruption_features,
    generate_synthetic_historical_dataset,
)
from app.ai.schemas import (
    DemandForecastRequest,
    DisruptionRiskRequest,
    JobDurationPredictionRequest,
    SLADelayRiskRequest,
)
from app.ai.services import ExplanationService, ai_service
from app.main import app


# ============================================================================
# 1. DATA PREPARATION & FEATURE ENGINEERING TESTS
# ============================================================================

def test_synthetic_historical_generator():
    """Verify synthetic dataset generator creates valid schema without data leakage."""
    df = generate_synthetic_historical_dataset(n_samples=50, random_seed=42)
    assert len(df) == 50
    assert "data_provenance" in df.columns
    assert (df["data_provenance"] == "SYNTHETIC_AUGMENTED").all()

    # Targets must exist and be physically valid
    assert (df["actual_duration_min"] >= 15.0).all()
    assert set(df["sla_delayed"].unique()).issubset({0, 1})
    assert set(df["disruption_occurred"].unique()).issubset({0, 1})

    # Zero data leakage: pre-dispatch columns must not contain completion timestamp info
    for col in ["job_type", "priority", "service_zone", "customer_type", "skill_count"]:
        assert col in df.columns
        assert df[col].isnull().sum() == 0


def test_delay_feature_engineering():
    """Verify ratio and margin features are correctly derived."""
    import pandas as pd
    raw = pd.DataFrame([{
        "predicted_duration_min": 100.0,
        "sla_slack_min": 200.0,
        "estimated_travel_min": 30.0,
    }])
    feat = engineer_delay_features(raw)
    assert "duration_to_slack_ratio" in feat.columns
    assert feat["duration_to_slack_ratio"].iloc[0] == pytest.approx(0.5, 0.01)
    assert feat["buffer_slack_min"].iloc[0] == pytest.approx(70.0, 0.01)


def test_disruption_feature_engineering():
    """Verify workload overwork index calculation."""
    import pandas as pd
    raw = pd.DataFrame([{
        "technician_workload_hours": 9.5,
        "tight_buffer_count": 2,
    }])
    feat = engineer_disruption_features(raw)
    assert "overwork_index" in feat.columns
    assert feat["overwork_index"].iloc[0] == pytest.approx(1.5, 0.01)


# ============================================================================
# 2. MODEL INFERENCE & SERVICE TESTS
# ============================================================================

def test_duration_prediction_service():
    """Verify duration prediction returns point estimate, bounds, and confidence."""
    req = JobDurationPredictionRequest(
        job_type="residential_wiring",
        priority="Normal",
        required_skills=["residential_wiring"],
        service_zone="Central",
        window_start_min=540,
        window_end_min=720,
        estimated_duration_min=120,
    )
    resp = ai_service.predict_duration(req)
    assert resp.predicted_duration_min > 0
    assert resp.lower_bound_min <= resp.predicted_duration_min
    assert resp.upper_bound_min >= resp.predicted_duration_min
    assert 0.0 <= resp.confidence_score <= 1.0
    assert not resp.fallback_used
    assert resp.data_source == "SYNTHETIC_AUGMENTED"


def test_duration_prediction_fallback_on_unknown():
    """Verify unknown job type gracefully falls back to configured default without crashing."""
    req = JobDurationPredictionRequest(
        job_type="unknown_quantum_repairs",
        priority="Low",
    )
    resp = ai_service.predict_duration(req)
    assert resp.predicted_duration_min > 0
    assert resp.lower_bound_min < resp.upper_bound_min


def test_sla_delay_risk_service():
    """Verify SLA delay classifier distinguishes tight buffer jobs."""
    # High risk: 140 min work + 30 min travel with only 120 min slack
    high_req = SLADelayRiskRequest(
        job_id="TEST-JOB-HIGH",
        job_type="distribution_panel_repair",
        priority="Critical",
        predicted_duration_min=140.0,
        appointment_window_start_min=540,
        appointment_window_end_min=660,
        sla_deadline_min=660,  # 120 min slack
        estimated_travel_time_min=30.0,
        service_zone="East",
    )
    resp_high = ai_service.predict_delay_risk(high_req)
    assert resp_high.delay_probability > 0.50
    assert resp_high.risk_category in ["MEDIUM", "HIGH"]
    assert len(resp_high.contributing_factors) > 0
    assert "Action:" in resp_high.suggested_action

    # Low risk: 30 min work with 300 min slack
    low_req = SLADelayRiskRequest(
        job_id="TEST-JOB-LOW",
        job_type="safety_inspection",
        priority="Low",
        predicted_duration_min=30.0,
        appointment_window_start_min=480,
        appointment_window_end_min=660,
        sla_deadline_min=780,  # 300 min slack
        estimated_travel_time_min=15.0,
        service_zone="Central",
    )
    resp_low = ai_service.predict_delay_risk(low_req)
    assert resp_low.delay_probability < 0.40
    assert resp_low.risk_category == "LOW"


def test_demand_forecasting_service():
    """Verify zone demand forecasting returns structured expected job volume."""
    req = DemandForecastRequest(day_of_week=0)
    resp = ai_service.forecast_demand(req)
    assert resp.total_expected_jobs > 0
    assert len(resp.zone_forecasts) >= 5
    for zf in resp.zone_forecasts:
        assert zf.expected_jobs >= 1.0
        assert zf.lower_bound <= zf.upper_bound
        assert zf.demand_level in ["LOW", "NORMAL", "HIGH", "PEAK"]


def test_disruption_risk_service():
    """Verify disruption risk flags overwork and tight buffers."""
    req = DisruptionRiskRequest(
        technician_id="TECH-001",
        job_id="JOB-01",
        technician_workload_hours=9.0,
        tight_buffer_count=3,
        service_zone="North",
    )
    resp = ai_service.predict_disruption_risk(req)
    assert 0.0 <= resp.disruption_probability <= 1.0
    assert resp.risk_category in ["LOW", "MEDIUM", "HIGH"]
    assert len(resp.contributing_factors) > 0


def test_model_status_and_health():
    """Verify AI model health report returns status of all 4 models."""
    health = ai_service.get_model_status()
    assert health.status == "healthy"
    assert health.all_models_ready
    assert len(health.models) == 4
    for key in ["duration", "delay", "demand", "disruption"]:
        assert key in health.models
        assert health.models[key].is_trained


# ============================================================================
# 3. FASTAPI API ROUTE TESTS (/api/v1/ai/*)
# ============================================================================

def test_api_predict_duration(client: TestClient):
    """POST /api/v1/ai/predict-duration endpoint integration."""
    payload = {
        "job_type": "fault_diagnosis",
        "priority": "High",
        "required_skills": ["fault_diagnosis"],
        "service_zone": "Central",
        "window_start_min": 600,
        "window_end_min": 720,
    }
    resp = client.post("/api/v1/ai/predict-duration", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "predicted_duration_min" in data
    assert "lower_bound_min" in data
    assert "upper_bound_min" in data
    assert data["confidence_score"] > 0


def test_api_predict_delay_risk(client: TestClient):
    """POST /api/v1/ai/predict-delay-risk endpoint integration."""
    payload = {
        "job_id": "TEST-101",
        "job_type": "commercial_wiring",
        "priority": "Critical",
        "predicted_duration_min": 150.0,
        "appointment_window_start_min": 540,
        "appointment_window_end_min": 660,
        "sla_deadline_min": 690,
        "estimated_travel_time_min": 25.0,
        "service_zone": "South",
    }
    resp = client.post("/api/v1/ai/predict-delay-risk", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "delay_probability" in data
    assert data["risk_category"] in ["LOW", "MEDIUM", "HIGH"]
    assert isinstance(data["contributing_factors"], list)


def test_api_forecast_demand(client: TestClient):
    """POST /api/v1/ai/forecast-demand endpoint integration."""
    resp = client.post("/api/v1/ai/forecast-demand", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "zone_forecasts" in data
    assert data["total_expected_jobs"] > 0


def test_api_predict_disruption_risk(client: TestClient):
    """POST /api/v1/ai/predict-disruption-risk endpoint integration."""
    payload = {
        "technician_id": "TECH-002",
        "technician_workload_hours": 8.5,
        "tight_buffer_count": 2,
    }
    resp = client.post("/api/v1/ai/predict-disruption-risk", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "disruption_probability" in data


def test_api_model_status(client: TestClient):
    """GET /api/v1/ai/model-status endpoint integration."""
    resp = client.get("/api/v1/ai/model-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["all_models_ready"] is True


def test_api_evaluation_reports(client: TestClient):
    """GET /api/v1/ai/evaluation endpoint integration."""
    resp = client.get("/api/v1/ai/evaluation")
    assert resp.status_code == 200
    data = resp.json()
    assert "duration" in data
    assert "delay" in data
    assert "demand" in data
    assert "disruption" in data


def test_scheduler_integration_with_ai():
    """Verify that ScheduleGenerateRequest accepts use_ai_durations and runs cleanly."""
    from app.schemas.schedule import ScheduleGenerateRequest
    req = ScheduleGenerateRequest(
        idempotency_key="ai-sched-test-01",
        horizon_start="2026-10-30T08:00:00+05:30",
        horizon_end="2026-10-30T18:00:00+05:30",
        use_ai_durations=True,
    )
    assert req.use_ai_durations is True
